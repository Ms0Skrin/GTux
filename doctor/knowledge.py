"""База знаний из интернета: оценки, сборки Proton и параметры запуска из отчётов игроков ProtonDB.

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
PROTON_DAYS = 365      # для выбора сборки — только последний год: сборки обновляются часто
# Поле responses.variant в отчёте: на чём игрок запускал игру. notListed (сборка не из списка
# сайта) не советуем — непонятно, что это за сборка.
VARIANTS = ("official", "experimental", "ge", "older", "native")

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


def summarize_reports(reports, since: float, proton_since: float | None = None) -> dict[str, dict]:
    """{appid: {"n": {вендор: отчётов с параметрами}, "t": {совет: {вендор: сколько}},
    "p": {вендор: {сборка: [отчётов, заработало]}}, "v": {сборка: {версия: сколько раз заработала}}}}."""
    proton_since = since if proton_since is None else proton_since
    games: dict[str, dict] = {}
    for rep in reports:
        ts = rep.get("timestamp", 0)
        if ts < min(since, proton_since):
            continue
        resp = rep.get("responses") or {}
        appid = ((rep.get("app") or {}).get("steam") or {}).get("appId")
        if not appid:
            continue
        vendor = gpu_vendor((rep.get("systemInfo") or {}).get("gpu") or "")
        g = games.setdefault(str(appid), {"n": Counter(), "t": {}, "p": {}, "v": {}})
        variant = resp.get("variant")
        if ts >= proton_since and variant in VARIANTS:
            works = resp.get("verdict") == "yes"
            stat = g["p"].setdefault(vendor, {}).setdefault(variant, [0, 0])
            stat[0] += 1
            stat[1] += works
            version = resp.get("customProtonVersion") if variant == "ge" else resp.get("protonVersion")
            if works and variant in ("ge", "older") and isinstance(version, str) and len(version) < 40:
                g["v"].setdefault(variant, Counter())[version.strip()] += 1
        opts = resp.get("launchOptions")
        if ts < since or not opts or not isinstance(opts, str):
            continue
        tokens = safe_tokens(opts)
        if not tokens:
            continue
        g["n"][vendor] += 1
        for tok in tokens:
            g["t"].setdefault(tok, Counter())[vendor] += 1
    # редкие советы не храним: файл в разы меньше
    result = {}
    for appid, g in games.items():
        g["n"] = dict(g["n"])
        g["t"] = {tok: dict(c) for tok, c in g["t"].items() if sum(c.values()) >= 2}
        if sum(st[0] for by_var in g["p"].values() for st in by_var.values()) < MIN_REPORTS:
            g["p"], g["v"] = {}, {}
        g["v"] = {var: dict(c.most_common(3)) for var, c in g["v"].items()}
        if g["t"] or g["p"]:
            result[appid] = {k: v for k, v in g.items() if v}
    return result


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
            now = time.time()
            games = summarize_reports(tracked(), now - RECENT_DAYS * 86400, now - PROTON_DAYS * 86400)

    tiers = {}
    for i, appid in enumerate(appids, 1):
        progress("tiers", i, len(appids))
        summary = fetch_summary(appid)
        if summary:
            tiers[appid] = summary
        time.sleep(0.2)  # не нагружаем сайт

    data = {"version": 2, "fetched": time.time(), "dump": name, "newest_report": newest,
            "license": LICENSE, "games": games, "tiers": tiers}
    tmp_path = kb_path().with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp_path, kb_path())
    load.cache_clear()
    log.info("knowledge updated: %s, %d games, %d tiers", name, len(games), len(tiers))
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


# ---------------- какая сборка Proton ----------------

def variant_of(tool: str | None) -> str:
    """Сборка, выбранная в Steam, в терминах ProtonDB: official, experimental, ge, cachyos, older, none.
    Официальные внутренние имена: proton_10, proton_experimental, proton_hotfix, proton_9 и т.д."""
    name = (tool or "").lower()
    if not name:
        return "none"
    family = build_family(name)
    if family != "valve":
        return family
    if "experimental" in name or "hotfix" in name:
        return "experimental"
    return "official" if re.fullmatch(r"proton_\d+", name) else "other"


def wilson(works: int, n: int, z: float = 1.64) -> float:
    """Нижняя граница доли «заработало» (интервал Уилсона, ~90%): 3 из 3 весит меньше, чем 30 из 31."""
    if n == 0:
        return 0.0
    p = works / n
    return (p + z * z / (2 * n) - z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5) / (1 + z * z / n)


@dataclass
class ProtonStat:
    variant: str
    reports: int
    works: int

    @property
    def share(self) -> float:
        return self.works / self.reports if self.reports else 0.0


@dataclass
class ProtonPick:
    best: ProtonStat | None          # None — нигде не работает или мало данных
    stats: list[ProtonStat]          # все сборки с данными, лучшие сначала
    same_vendor: bool                # считали только отчёты с такой же видеокартой
    versions: list[str]              # для ge/older: версии, которые чаще всего называли рабочими
    close: bool = False              # вторая сборка почти так же хороша
    broken: bool = False             # отчёты есть, но почти ни у кого не работает


# при равенстве — самая простая: официальный Proton ставится сам, остальное — нет
PREFER = {"native": 0, "official": 1, "experimental": 2, "ge": 3, "older": 4}


def proton_for(appid: str, profile: Profile, data: dict | None = None) -> ProtonPick | None:
    """Сборка, на которой игра чаще всего работает у игроков с такой же видеокартой. None — нет данных."""
    data = load() if data is None else data
    game = (data.get("games") or {}).get(appid) or {}
    by_vendor = game.get("p") or {}
    if not by_vendor:
        return None
    own = by_vendor.get(profile.vendor, {})
    same = sum(st[0] for st in own.values()) >= SAME_VENDOR_MIN
    counts: dict[str, list[int]] = {}
    for vendor, variants in by_vendor.items():
        if same and vendor != profile.vendor:
            continue
        for var, (n, works) in variants.items():
            if var in VARIANTS:
                c = counts.setdefault(var, [0, 0])
                c[0] += n
                c[1] += works
    stats = [ProtonStat(var, n, works) for var, (n, works) in counts.items()]
    stats.sort(key=lambda s: (-wilson(s.works, s.reports), PREFER[s.variant]))
    if not stats:
        return None
    pick = ProtonPick(None, stats, same, [])
    total, works = sum(s.reports for s in stats), sum(s.works for s in stats)
    if total >= MIN_REPORTS and works / total < 0.2:
        pick.broken = True
        return pick
    candidates = [s for s in stats if s.reports >= MIN_REPORTS and s.share >= 0.5]
    if not candidates:
        return pick
    # из почти равных (разница меньше 5 процентных пунктов) берём самую простую
    top = wilson(candidates[0].works, candidates[0].reports)
    near = [s for s in candidates if top - wilson(s.works, s.reports) < 0.05]
    best = min(near, key=lambda s: PREFER[s.variant])
    pick.best = best
    pick.close = len(near) > 1
    pick.versions = list((game.get("v") or {}).get(best.variant, {}))
    return pick


def installed_variants(official: list[str], custom: list[str]) -> dict[str, list[str]]:
    """Установленные сборки по видам: official, experimental, ge, cachyos. Новые версии сначала.
    official — папки steamapps/common/Proton*, custom — имена из compatibilitytools.d."""
    def version(name: str) -> tuple[int, ...]:
        return tuple(int(x) for x in re.findall(r"\d+", name))
    found: dict[str, list[str]] = {}
    for name in official:
        var = "experimental" if re.search(r"experimental|hotfix", name, re.I) else "official"
        found.setdefault(var, []).append(name)
    for name in custom:
        fam = build_family(name)
        if fam != "valve":
            found.setdefault(fam, []).append(name)
    return {var: sorted(names, key=version, reverse=True) for var, names in found.items()}


@dataclass
class Advice:
    """Что показать человеку о сборке Proton для игры."""
    pick: ProtonPick
    current: str                 # вид сборки, выбранной сейчас (variant_of)
    use: str | None = None       # какую из установленных выбрать
    missing: bool = False        # подходящая сборка не установлена

    @property
    def matches(self) -> bool:
        best = self.pick.best
        return best is not None and best.variant == self.current


def advise(pick: ProtonPick, tool: str | None, installed: dict[str, list[str]], native: bool = False) -> Advice:
    adv = Advice(pick, "native" if native and not tool else variant_of(tool))
    best = pick.best
    if best is None or best.variant == "native":
        return adv
    if best.variant == "older":
        # конкретную старую версию Steam ставит сам, её выбирают в списке совместимости
        adv.use = pick.versions[0] if pick.versions else None
        return adv
    names = installed.get(best.variant, [])
    if names:
        adv.use = names[0]
    else:
        adv.missing = True
        adv.use = pick.versions[0] if pick.versions else None
    return adv
