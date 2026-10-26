"""Группа: разбор логов Proton (steam-<appid>.log, включаются через PROTON_LOG=1).

Ищем только сообщения, текст которых сверен с исходниками:
  Wine dlls/ntdll/loader.c:  "Library %s (which is needed by %s) not found", "could not load %s"
  Wine programs/winedbg:     "Unhandled exception"
  DXVK:                      VK_ERROR_DEVICE_LOST (код ошибки Vulkan)
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from doctor import gamedb
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result

GROUP = "logs"

MAX_LOGS = 10
TAIL_BYTES = 8 * 1024 * 1024  # логи бывают по гигабайту — читаем только конец

MISSING_DLL = re.compile(r"err:module:import_dll Library (\S+) \(which is needed by (.+?)\) not found")
CRASH = re.compile(r"Unhandled (?:exception|page fault)")
DEVICE_LOST = re.compile(r"VK_ERROR_DEVICE_LOST")
BROKEN_PREFIX = re.compile(r"could not load (?:L\")?\S*(?:kernel32|ntdll)\.dll", re.I)

# DLL -> пакет winetricks (ставится через protontricks <appid> <пакет>)
DLL_VERBS = [
    (re.compile(r"^(msvcp140(_\d)?|vcruntime140(_\d)?|concrt140)\.dll$", re.I), "vcrun2022"),
    (re.compile(r"^d3dx9_\d+\.dll$", re.I), "d3dx9"),
    (re.compile(r"^d3dcompiler_47\.dll$", re.I), "d3dcompiler_47"),
]


def log_dir() -> Path:
    return Path(os.environ.get("PROTON_LOG_DIR") or Path.home())


def read_tail(path: Path, limit: int = TAIL_BYTES) -> str:
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - limit))
        return f.read().decode("utf-8", errors="replace")


def analyze(text: str, appid: str) -> list[tuple[Status, str, str | None]]:
    """[(статус, пояснение, команда)] по тексту лога."""
    findings: list[tuple[Status, str, str | None]] = []
    if BROKEN_PREFIX.search(text):
        findings.append((Status.FAIL, t("logs.broken_prefix", appid=appid), None))
    dlls = list(dict.fromkeys(m[1] for m in MISSING_DLL.finditer(text)))
    if dlls:
        verbs = list(dict.fromkeys(v for d in dlls for rx, v in DLL_VERBS if rx.match(d)))
        fix = f"protontricks {appid} {' '.join(verbs)}" if verbs else None
        findings.append((Status.FAIL, t("logs.missing_dll", dlls=", ".join(dlls[:6])), fix))
    if DEVICE_LOST.search(text):
        findings.append((Status.WARN, t("logs.device_lost"), None))
    if CRASH.search(text):
        findings.append((Status.WARN, t("logs.crash"), None))
    return findings


@check("proton")
def check_logs(ctx: Context):
    logs = sorted(log_dir().glob("steam-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_LOGS]
    if not logs:
        return result(GROUP, "proton", Status.OK, value=t("logs.none"))
    names = {g.appid: g.name for g in gamedb.installed_games(ctx.steam_libraries)} if ctx.steam_libraries else {}
    results = []
    for path in logs:
        appid = path.stem.removeprefix("steam-")
        stat = path.stat()
        value = t("logs.value", path=path, date=time.strftime("%d.%m %H:%M", time.localtime(stat.st_mtime)),
                  size=f"{stat.st_size / 1024**2:.1f}")
        try:
            findings = analyze(read_tail(path), appid)
        except OSError as e:
            results.append(result(GROUP, f"proton.{appid}", Status.UNKNOWN, title=names.get(appid, appid),
                                  value=value, error=str(e)))
            continue
        severity = [Status.OK, Status.UNKNOWN, Status.WARN, Status.FAIL]
        status = max((s for s, _, _ in findings), key=severity.index, default=Status.OK)
        fixes = [f for _, _, f in findings if f]
        hint = "\n".join(h for _, h, _ in findings)
        if status != Status.OK:
            hint += "\n" + t("games.protondb", appid=appid)
        else:
            value += "\n" + t("logs.clean")
        results.append(result(GROUP, f"proton.{appid}", status, title=t("logs.title_for", name=names.get(appid, appid)),
                              value=value, hint=hint, fix=" && ".join(fixes) or None))
    return results


CHECKS = [check_logs]
