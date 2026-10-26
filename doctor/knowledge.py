"""База знаний из интернета: оценки и параметры запуска из отчётов игроков ProtonDB.

Источники (скачиваются только по кнопке «Обновить базу» или `--update-kb`):
  - выгрузка отчётов: https://github.com/bdefore/protondb-data (ODbL), раз в месяц, архив ~70 МБ;
  - оценка игры: https://www.protondb.com/api/v1/reports/summaries/<appid>.json (неофициальный API).
Проверки читают только готовый файл knowledge.json и в интернет не ходят.

Советы берутся из отчётов, но в Steam попадает только то, что есть в белом списке ниже:
каждая переменная описана в официальной документации (ссылка в source). Команды оболочки,
неизвестные программы и странные значения отбрасываются: строку из интернета нельзя
выполнять как есть.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import tarfile
import tempfile
import time
import urllib.request
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from doctor import __version__
from doctor.launchopts import ENV_ASSIGN, Parsed

log = logging.getLogger("doctor.knowledge")

REPO_API = "https://api.github.com/repos/bdefore/protondb-data/contents/reports"
RAW = "https://raw.githubusercontent.com/bdefore/protondb-data/master/reports/"
SUMMARY = "https://www.protondb.com/api/v1/reports/summaries/{appid}.json"
LICENSE = "ProtonDB reports, Open Database License (ODbL): https://github.com/bdefore/protondb-data"
USER_AGENT = f"linux-gamer-doctor/{__version__}"

RECENT_DAYS = 730      # старые отчёты не учитываем: Proton и драйверы с тех пор сильно поменялись
MIN_REPORTS = 3        # меньше — это мнение одного-двух человек, а не совет
MIN_SHARE = 0.15       # доля отчётов с параметрами, где встречается этот совет
SAME_VENDOR_MIN = 5    # столько отчётов с такой же видеокартой нужно, чтобы считать только их

PROTON = "https://github.com/ValveSoftware/Proton/blob/proton_10.0/README.md"
GE = "https://github.com/GloriousEggroll/proton-ge-custom/blob/master/README.md"
CACHYOS = "https://github.com/CachyOS/proton-cachyos/blob/cachyos_main/README.md"
GE_CACHY = ("ge", "cachyos")  # переменная есть в README обеих сборок
VKD3D = "https://github.com/HansKristian-Work/vkd3d-proton/blob/master/README.md"
ONE = r"1"


@dataclass(frozen=True)
class Rule:
    values: str                  # регулярное выражение для значения
    needs: tuple[str, ...] = ()  # nvidia | amd | wayland — иначе совет не показываем
    builds: tuple[str, ...] = () # только в этих сборках Proton (ge, cachyos); пусто — в любой
    source: str = PROTON
    experimental: bool = False   # документация сама предупреждает о проблемах — сразу не включаем


# Что программа может советовать. Только документированное.
ENV_RULES: dict[str, Rule] = {
    # Proton (Valve), README, таблица переменных
    "PROTON_NO_D3D11": Rule(ONE),
    "PROTON_NO_D3D10": Rule(ONE),
    "PROTON_DXVK_D3D8": Rule(ONE),
    "PROTON_NO_ESYNC": Rule(ONE),
    "PROTON_NO_FSYNC": Rule(ONE),
    "PROTON_DISABLE_NVAPI": Rule(ONE, ("nvidia",)),
    "PROTON_HEAP_DELAY_FREE": Rule(ONE),
    "PROTON_SET_GAME_DRIVE": Rule(ONE),
    "PROTON_OLD_GL_STRING": Rule(ONE),
    "PROTON_HIDE_NVIDIA_GPU": Rule(ONE, ("nvidia",)),
    "WINE_DISABLE_VULKAN_OPWR": Rule(ONE, ("wayland",)),
    "WINE_FULLSCREEN_INTEGER_SCALING": Rule(ONE),
    "WINE_DO_NOT_CREATE_DXGI_DEVICE_MANAGER": Rule(ONE),
    # GE-Proton и proton-cachyos, README (сверено по обоим: есть ли переменная в таблице)
    "PROTON_ENABLE_NVAPI": Rule(ONE, ("nvidia",), ("ge",), GE),
    "PROTON_DLSS_UPGRADE": Rule(r"1|\d+(\.\d+)*", ("nvidia",), GE_CACHY, GE),
    "PROTON_FSR4_UPGRADE": Rule(r"1|\d+(\.\d+)*", ("amd",), GE_CACHY, GE),
    # README proton-cachyos: «winewayland is experimental and work-in-progress, expect issues»
    "PROTON_ENABLE_WAYLAND": Rule(ONE, ("wayland",), GE_CACHY, GE, experimental=True),
    "PROTON_USE_WAYLAND": Rule(ONE, ("wayland",), GE_CACHY, GE, experimental=True),
    "PROTON_NO_NTSYNC": Rule(ONE, (), ("ge",), GE),
    "PROTON_USE_WOW64": Rule(ONE, (), GE_CACHY, GE),
    "PROTON_PREFER_SDL": Rule(ONE, (), GE_CACHY, GE),
    "PROTON_USE_SDL": Rule(ONE, (), GE_CACHY, GE),
    "PROTON_NO_WRITE_WATCH": Rule(ONE, (), ("ge",), GE),
    # VKD3D-Proton, README
    "VKD3D_CONFIG": Rule(r"[a-z0-9_]+(,[a-z0-9_]+)*", source=VKD3D),
    "VKD3D_FRAME_RATE": Rule(r"\d{1,3}", source=VKD3D),
    # Wine: man wine (WINEDLLOVERRIDES); PipeWire: man pipewire-pulse (PULSE_LATENCY_MSEC)
    "WINEDLLOVERRIDES": Rule(r"[A-Za-z0-9_.,*-]+=[nbd,]*(;[A-Za-z0-9_.,*-]+=[nbd,]*)*",
                             source="https://gitlab.winehq.org/wine/wine/-/wikis/Man-Pages/wine"),
    "PULSE_LATENCY_MSEC": Rule(r"\d{1,3}", source="man pipewire-pulse"),
}
# Обёртки: (программа, которая должна быть установлена)
# MangoHud не советуем: это оверлей по вкусу, а не исправление.
WRAPPER_RULES = {"gamemoderun": "gamemoderun", "game-performance": "game-performance"}
# Есть только в CachyOS (пакет cachyos-settings) — на других системах не предлагаем вовсе.
DISTRO_TOOLS = {"game-performance"}
# Аргументы игры: только простые флаги вида -novid / --skip-launcher / -dx11
GAME_ARG = re.compile(r"[-+]{1,2}[A-Za-z][A-Za-z0-9_.-]{0,40}")


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "linux-gamer-doctor"


def kb_path() -> Path:
    return cache_dir() / "knowledge.json"


# ---------------- разбор одного отчёта ----------------

def gpu_vendor(text: str) -> str:
    s = text.lower()
    if re.search(r"nvidia|geforce|\brtx\b|\bgtx\b|quadro", s):
        return "nvidia"
    if re.search(r"\bamd\b|radeon|\bradv\b|\bnavi\b|\bvega\b", s):
        return "amd"
    if "intel" in s:
        return "intel"
    return "other"


def safe_tokens(opts: str) -> set[str]:
    """Из строки игрока — только то, что разрешено белым списком: «VAR=значение», обёртка или «arg:-флаг»."""
    try:
        tokens = shlex.split(opts)
    except ValueError:
        return set()
    if "%command%" not in tokens:
        return set()
    i = tokens.index("%command%")
    found = set()
    for tok in tokens[:i]:
        m = ENV_ASSIGN.match(tok)
        if m:
            rule = ENV_RULES.get(m[1])
            if rule and re.fullmatch(rule.values, m[2]):
                found.add(f"{m[1]}={m[2]}")
        elif tok in WRAPPER_RULES:
            found.add(tok)
    for tok in tokens[i + 1:]:
        if GAME_ARG.fullmatch(tok):
            found.add("arg:" + tok)
    return found


def iter_reports(stream):
    """Отчёты из огромного JSON-массива по одному, не читая весь файл в память."""
    decoder = json.JSONDecoder()
    buf = ""
    while True:
        chunk = stream.read(1 << 20)
        if not chunk:
            break
        buf += chunk.decode("utf-8", errors="replace")
        while True:
            buf = buf.lstrip(" \n\r\t,[")
            if not buf or buf[0] == "]":
                break
            try:
                obj, end = decoder.raw_decode(buf)
            except ValueError:
                break  # объект ещё не дочитан
            buf = buf[end:]
            yield obj


def summarize_reports(reports, since: float) -> dict[str, dict]:
    """{appid: {"n": {вендор: отчётов с параметрами}, "t": {совет: {вендор: сколько}}}}."""
    games: dict[str, dict] = {}
    for rep in reports:
        if rep.get("timestamp", 0) < since:
            continue
        opts = (rep.get("responses") or {}).get("launchOptions")
        appid = ((rep.get("app") or {}).get("steam") or {}).get("appId")
        if not opts or not isinstance(opts, str) or not appid:
            continue
        tokens = safe_tokens(opts)
        if not tokens:
            continue
        vendor = gpu_vendor((rep.get("systemInfo") or {}).get("gpu") or "")
        g = games.setdefault(str(appid), {"n": Counter(), "t": {}})
        g["n"][vendor] += 1
        for tok in tokens:
            g["t"].setdefault(tok, Counter())[vendor] += 1
    # редкие советы не храним: файл в разы меньше
    for g in games.values():
        g["n"] = dict(g["n"])
        g["t"] = {tok: dict(c) for tok, c in g["t"].items() if sum(c.values()) >= 2}
    return {a: g for a, g in games.items() if g["t"]}


# ---------------- скачивание ----------------

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _get(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def latest_dump_name(names: list[str]) -> str | None:
    """reports_sep1_2026.tar.gz → самый свежий по (год, месяц, число)."""
    best = None
    for name in names:
        m = re.fullmatch(r"reports_([a-z]{3})(\d{1,2})_(\d{4})\.tar\.gz", name)
        if m and m[1] in MONTHS:
            key = (int(m[3]), MONTHS.index(m[1]), int(m[2]))
            if best is None or key > best[0]:
                best = (key, name)
    return best[1] if best else None


def download(url: str, dest: Path, progress, attempts: int = 5) -> None:
    """Скачивает файл; при обрыве продолжает с места остановки (GitHub отвечает 206 на Range)."""
    total = 0
    for attempt in range(1, attempts + 1):
        done = dest.stat().st_size if dest.exists() else 0
        if total and done >= total:
            return
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        if done:
            req.add_header("Range", f"bytes={done}-")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if done and resp.status != 206:
                    done = 0  # сервер не умеет докачку — начинаем заново
                total = done + int(resp.headers.get("Content-Length") or 0)
                with open(dest, "ab" if done else "wb") as out:
                    while chunk := resp.read(1 << 16):
                        out.write(chunk)
                        done += len(chunk)
                        progress(done, total)
            if not total or done >= total:
                return
        except OSError as e:
            if attempt == attempts:
                raise
            log.info("download interrupted at %d bytes (%s), retry %d", done, e, attempt)
            time.sleep(2 * attempt)


def fetch_summary(appid: str) -> dict | None:
    try:
        with _get(SUMMARY.format(appid=appid), timeout=20) as resp:
            data = json.load(resp)
    except (OSError, ValueError) as e:
        log.info("protondb summary %s: %s", appid, e)
        return None  # у игры может не быть отчётов — тогда ProtonDB отвечает 404
    return {k: data.get(k) for k in ("tier", "trendingTier", "total", "confidence")}


def update(appids: list[str], progress=lambda stage, done=0, total=0: None) -> dict:
    """Скачивает выгрузку и оценки, сохраняет knowledge.json. Долго: минута-две."""
    progress("list")
    with _get(REPO_API, timeout=30) as resp:
        names = [item["name"] for item in json.load(resp)]
    name = latest_dump_name(names)
    if not name:
        raise RuntimeError("в репозитории protondb-data не нашлось выгрузок")

    cache_dir().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir()) as tmp:
        archive = Path(tmp) / name
        download(RAW + name, archive, lambda done, total: progress("download", done, total))
        progress("parse")
        with tarfile.open(archive) as tf:
            member = next((m for m in tf if m.isfile() and m.name.endswith(".json")), None)
            if member is None:
                raise RuntimeError(f"в {name} нет JSON")
            newest = 0.0

            def tracked():
                nonlocal newest
                for rep in iter_reports(tf.extractfile(member)):
                    newest = max(newest, rep.get("timestamp", 0))
                    yield rep
            games = summarize_reports(tracked(), time.time() - RECENT_DAYS * 86400)

    tiers = {}
    for i, appid in enumerate(appids, 1):
        progress("tiers", i, len(appids))
        summary = fetch_summary(appid)
        if summary:
            tiers[appid] = summary
        time.sleep(0.2)  # не нагружаем сайт

    data = {"version": 1, "fetched": time.time(), "dump": name, "newest_report": newest,
            "license": LICENSE, "games": games, "tiers": tiers}
    tmp_path = kb_path().with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp_path, kb_path())
    load.cache_clear()
    log.info("knowledge updated: %s, %d games with tips, %d tiers", name, len(games), len(tiers))
    return data


@cache
def load() -> dict:
    try:
        return json.loads(kb_path().read_text())
    except (OSError, ValueError):
        return {}


# ---------------- личные советы ----------------

@dataclass
class Profile:
    """Что важно для советов о конкретном компьютере."""
    vendor: str              # nvidia | amd | intel | other
    wayland: bool
    tools: frozenset[str]    # установленные обёртки


@dataclass
class Tip:
    token: str               # «VAR=значение», обёртка или «arg:-флаг»
    count: int
    reports: int
    same_vendor: bool        # считали только отчёты с такой же видеокартой
    builds: tuple[str, ...] = ()  # работает только в этих сборках Proton
    experimental: bool = False
    missing_tool: str = ""   # обёртка не установлена

    @property
    def share(self) -> float:
        return self.count / self.reports if self.reports else 0.0

    @property
    def text(self) -> str:
        return self.token[4:] if self.token.startswith("arg:") else self.token

    def as_parsed(self) -> Parsed:
        if self.token.startswith("arg:"):
            return Parsed(args=[self.token[4:]])
        m = ENV_ASSIGN.match(self.token)
        return Parsed(env={m[1]: m[2]}) if m else Parsed(wrappers=[self.token])


def profile_from(ctx, which=None) -> Profile:
    from doctor.system import which as default_which
    which = which or default_which
    vendors = [g.vendor for g in getattr(ctx, "gpus", [])]
    # у ноутбука две видеокарты: игры идут на дискретной
    vendor = next((v for v in vendors if v in ("nvidia", "amd")), vendors[0] if vendors else "other")
    wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
    return Profile(vendor, wayland, frozenset(w for w, binary in WRAPPER_RULES.items() if which(binary)))


def tips_for(appid: str, profile: Profile, data: dict | None = None, limit: int = 8) -> list[Tip]:
    data = load() if data is None else data
    game = (data.get("games") or {}).get(appid)
    if not game:
        return []
    n = game.get("n", {})
    same = n.get(profile.vendor, 0) >= SAME_VENDOR_MIN
    reports = n.get(profile.vendor, 0) if same else sum(n.values())
    tips = []
    for token, by_vendor in game.get("t", {}).items():
        count = by_vendor.get(profile.vendor, 0) if same else sum(by_vendor.values())
        if count < MIN_REPORTS or count / reports < MIN_SHARE:
            continue
        tip = Tip(token, count, reports, same)
        m = ENV_ASSIGN.match(token)
        if m:
            rule = ENV_RULES.get(m[1])
            if rule is None or not re.fullmatch(rule.values, m[2]):
                continue  # база могла быть собрана старой версией с другим списком
            if "nvidia" in rule.needs and profile.vendor != "nvidia":
                continue
            if "amd" in rule.needs and profile.vendor != "amd":
                continue
            if "wayland" in rule.needs and not profile.wayland:
                continue
            tip.builds, tip.experimental = rule.builds, rule.experimental
        elif token in WRAPPER_RULES:
            if token not in profile.tools:
                if token in DISTRO_TOOLS:
                    continue
                tip.missing_tool = WRAPPER_RULES[token]
        elif not (token.startswith("arg:") and GAME_ARG.fullmatch(token[4:])):
            continue
        elif "steamdeck" in token.lower():
            continue  # аргументы «для Steam Deck» на обычном ПК не советуем
        tips.append(tip)
    tips.sort(key=lambda t: (-t.share, t.token))
    # из нескольких значений одной переменной оставляем самое частое
    seen, result = set(), []
    for tip in tips:
        key = tip.token.split("=", 1)[0]
        if key not in seen:
            seen.add(key)
            result.append(tip)
    return result[:limit]


def tier_for(appid: str, data: dict | None = None) -> dict | None:
    data = load() if data is None else data
    return (data.get("tiers") or {}).get(appid)


BUILD_NAMES = {"ge": "GE-Proton", "cachyos": "proton-cachyos"}


def build_family(tool: str | None) -> str:
    """Семейство сборки по внутреннему имени из config.vdf: ge (GE-Proton10-25, Proton-9.0-GE),
    cachyos (proton-cachyos-…), иначе valve (официальный Proton или не выбран)."""
    parts = re.split(r"[-_.\s]+", (tool or "").lower())
    if "ge" in parts:
        return "ge"
    if "cachyos" in parts:
        return "cachyos"
    return "valve"


def works_with(tip: "Tip", tool: str | None) -> bool:
    return not tip.builds or build_family(tool) in tip.builds
