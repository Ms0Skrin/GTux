"""Вся библиотека Steam, включая неустановленные игры, — без ключа Steam Web API, только из файлов Steam.

Источники:
  - appcache/librarycache/<appid>/ — Steam скачивает обложки для игр из библиотеки;
  - userdata/<id>/config/localconfig.vdf — игры, которые запускались;
  - steamapps/appmanifest_*.acf — установленные;
  - appcache/appinfo.vdf — название, тип (game/tool/dlc…) и ОС игры. Двоичный формат v28/v29,
    описан в https://github.com/SteamDatabase/SteamAppInfo (заголовок, записи, двоичный KeyValues,
    в v29 ключи — номера в таблице строк в конце файла).
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from pathlib import Path

from gtux import gamedb, knowledge, steamcfg, vdf
from gtux.i18n import t
from gtux.models import Status

log = logging.getLogger("gtux.library")

MAGIC_V28 = 0x07564428
MAGIC_V29 = 0x07564429
ENTRY_HEADER = 4 + 4 + 8 + 20 + 4 + 20  # infoState, lastUpdated, picsToken, sha1, changeNumber, binary sha1


class AppInfoError(Exception):
    pass


def _cstring(b: bytes, off: int) -> tuple[str, int]:
    end = b.index(b"\0", off)
    return b[off:end].decode("utf-8", "replace"), end + 1


def _read_kv(b: bytes, off: int, strings: list[str] | None) -> tuple[dict, int]:
    """Двоичный KeyValues: тип (1 байт), ключ, значение; 0x08 — конец раздела."""
    node: dict = {}
    while True:
        kind = b[off]
        off += 1
        if kind == 0x08:
            return node, off
        if strings is None:
            key, off = _cstring(b, off)
        else:
            (idx,) = struct.unpack_from("<i", b, off)
            off += 4
            key = strings[idx] if 0 <= idx < len(strings) else str(idx)
        key = key.lower()
        if kind == 0x00:
            node[key], off = _read_kv(b, off, strings)
        elif kind == 0x01:
            node[key], off = _cstring(b, off)
        elif kind in (0x02, 0x04, 0x06):
            (node[key],) = struct.unpack_from("<i", b, off)
            off += 4
        elif kind == 0x03:
            (node[key],) = struct.unpack_from("<f", b, off)
            off += 4
        elif kind in (0x07, 0x0A):
            (node[key],) = struct.unpack_from("<Q" if kind == 0x07 else "<q", b, off)
            off += 8
        else:
            raise AppInfoError(f"unknown KeyValues type {kind:#x} at {off}")


def parse_appinfo(data: bytes, wanted: set[str] | None = None) -> dict[str, dict]:
    """{appid: раздел common (name, type, oslist…)} для appid из wanted (None — для всех)."""
    if len(data) < 16:
        raise AppInfoError("file too short")
    magic, _universe = struct.unpack_from("<II", data, 0)
    strings = None
    off = 8
    if magic == MAGIC_V29:
        (table,) = struct.unpack_from("<q", data, 8)
        off = 16
        (count,) = struct.unpack_from("<I", data, table)
        strings = [s.decode("utf-8", "replace") for s in data[table + 4:].split(b"\0")[:count]]
    elif magic != MAGIC_V28:
        raise AppInfoError(f"unsupported appinfo.vdf version {magic:#x}")
    result: dict[str, dict] = {}
    while off + 8 <= len(data):
        appid, size = struct.unpack_from("<II", data, off)
        if appid == 0:
            break
        start, off = off + 8, off + 8 + size
        if wanted is not None and str(appid) not in wanted:
            continue
        try:
            kv, _ = _read_kv(data, start + ENTRY_HEADER, strings)
        except (AppInfoError, IndexError, ValueError, struct.error) as e:
            log.debug("appinfo %s: %s", appid, e)
            continue
        common = kv.get("appinfo", {}).get("common", {})
        if isinstance(common, dict):
            result[str(appid)] = common
    return result


@dataclass
class LibraryGame:
    appid: str
    name: str
    installed: bool
    linux: bool                       # у игры есть Linux-версия (oslist в appinfo)
    pick: knowledge.ProtonPick | None  # что работает у игроков с такой же видеокартой
    anticheat: dict | None            # запись AreWeAntiCheatYet


def library_appids(root: Path) -> set[str]:
    ids = {p.name for p in (root / "appcache" / "librarycache").glob("*") if p.name.isdigit()}
    config = steamcfg.localconfig_path(root)
    if config is not None:
        try:
            apps = vdf.loads(config.read_text(errors="replace"))
            for k in steamcfg.APPS_PATH:
                apps = apps.get(k, {})
            ids |= {a for a in apps if a.isdigit()}
        except (OSError, vdf.VDFError):
            pass
    return ids


def scan(roots: list[Path], libraries: list[Path], profile: knowledge.Profile | None,
         data: dict | None = None) -> list[LibraryGame]:
    """Игры библиотеки: названия и типы из appinfo.vdf; служебные (Proton, рантаймы, DLC) отбрасываются."""
    installed = {g.appid: g.name for g in gamedb.installed_games([lib for lib in libraries if lib.exists()])}
    wanted = set(installed)
    info: dict[str, dict] = {}
    for root in roots:
        wanted |= library_appids(root)
        try:
            info.update(parse_appinfo((root / "appcache" / "appinfo.vdf").read_bytes(), wanted))
        except (OSError, AppInfoError, struct.error) as e:
            log.info("appinfo %s: %s", root, e)
    data = knowledge.load() if data is None else data
    prof = profile or knowledge.Profile("other", False, frozenset())
    games = []
    for appid in wanted:
        common = info.get(appid, {})
        kind = str(common.get("type", "game" if appid in installed else "")).lower()
        name = common.get("name") or installed.get(appid)
        if kind != "game" or not name or gamedb.NOT_GAMES.search(name):
            continue
        games.append(LibraryGame(appid, name, appid in installed, "linux" in str(common.get("oslist", "")).lower(),
                                 knowledge.proton_for(appid, prof, data), gamedb.anticheat_db().get(appid)))
    return sorted(games, key=lambda g: (not g.installed, g.name.lower()))


AC_SHORT = {"Supported": "ok", "Running": "running", "Planned": "planned", "Broken": "broken", "Denied": "denied"}


def summary(g: LibraryGame) -> tuple[Status, list[str]]:
    """Итог по игре для списка: статус (худший из «сборка» и «античит») и короткие пояснения."""
    parts = [t("lib.installed") if g.installed else t("lib.not_installed")]
    if g.linux:
        parts.append(t("lib.linux"))
    pick = g.pick
    if pick and pick.broken:
        status = Status.FAIL
        parts.append(t("lib.broken", works=sum(s.works for s in pick.stats), total=sum(s.reports for s in pick.stats)))
    elif pick and pick.best:
        status = Status.OK
        parts.append(t("lib.best", name=t(f"rec.variant.{pick.best.variant}"), works=pick.best.works,
                       total=pick.best.reports))
    else:
        status = Status.UNKNOWN
        parts.append(t("lib.no_data"))
    ac = (g.anticheat or {}).get("status")
    if ac in AC_SHORT:
        parts.append(t(f"lib.ac.{AC_SHORT[ac]}"))
        if ac in ("Planned", "Broken", "Denied") and status != Status.FAIL:
            status = Status.WARN
    return status, parts
