"""Данные об играх: установленные игры Steam, их настройки и база заметок.

Источники:
  - steamapps/appmanifest_*.acf — какие игры установлены;
  - config/config.vdf (CompatToolMapping) — какой Proton выбран для игры;
  - userdata/<id>/config/localconfig.vdf (LaunchOptions) — параметры запуска;
  - gtux/data/games.toml — ручные заметки с источниками;
  - gtux/data/anticheat.json — снимок AreWeAntiCheatYet.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from gtux import steamcfg, vdf

DATA = Path(__file__).parent / "data"

# Служебные «приложения» Steam — не игры.
NOT_GAMES = re.compile(r"^(Proton\b|Steam Linux Runtime|Steamworks Common Redistributables)", re.I)


@dataclass
class Game:
    appid: str
    name: str
    library: Path


def installed_games(libraries: list[Path]) -> list[Game]:
    games: dict[str, Game] = {}
    for lib in libraries:
        for manifest in sorted((lib / "steamapps").glob("appmanifest_*.acf")):
            try:
                state = vdf.loads(manifest.read_text(errors="replace")).get("appstate", {})
            except (OSError, vdf.VDFError):
                continue  # битый манифест не должен ломать весь список
            appid, name = state.get("appid"), state.get("name", "")
            if appid and not NOT_GAMES.search(name):
                games.setdefault(appid, Game(appid, name or appid, lib))
    return sorted(games.values(), key=lambda g: g.name.lower())


def _load_vdf(path: Path) -> dict:
    try:
        return vdf.loads(path.read_text(errors="replace"))
    except (OSError, vdf.VDFError):
        return {}


def compat_mapping(root: Path) -> dict[str, str]:
    """{appid: внутреннее имя сборки}; ключ "0" — сборка по умолчанию для всех игр."""
    steam = (_load_vdf(root / "config" / "config.vdf").get("installconfigstore", {})
             .get("software", {}).get("valve", {}).get("steam", {}))
    mapping = steam.get("compattoolmapping", {})
    return {appid: v["name"].lower() for appid, v in mapping.items()
            if isinstance(v, dict) and v.get("name")}


def launch_options(root: Path) -> dict[str, str]:
    """{appid: параметры запуска} из localconfig.vdf последнего активного пользователя."""
    config = steamcfg.localconfig_path(root)
    if config is None:
        return {}
    apps = (_load_vdf(config).get("userlocalconfigstore", {}).get("software", {})
            .get("valve", {}).get("steam", {}).get("apps", {}))
    return {appid: v["launchoptions"] for appid, v in apps.items()
            if isinstance(v, dict) and v.get("launchoptions", "").strip()}


@dataclass
class SteamSettings:
    """Игра Steam вместе с тем, что нужно странице «Параметры запуска»."""
    game: Game
    config: Path | None     # localconfig.vdf, куда писать параметры
    options: str            # текущие параметры запуска
    tool: str | None        # сборка Proton, выбранная для игры (или по умолчанию)
    native: bool = False    # Linux-версия без сборки, выбранной вручную: сборка по умолчанию к ней не применяется


def steam_settings(roots: list[Path], libraries: list[Path]) -> list[SteamSettings]:
    mapping, options, config = {}, {}, None
    for root in roots:
        mapping.update(compat_mapping(root))
        options.update(launch_options(root))
        config = config or steamcfg.localconfig_path(root)
    result = []
    for g in installed_games([lib for lib in libraries if lib.exists()]):
        forced = mapping.get(g.appid)
        native = not forced and is_native(g.appid)
        tool = forced or (None if native else mapping.get("0"))
        result.append(SteamSettings(g, config, options.get(g.appid, ""), tool, native))
    return result


@cache
def notes_db() -> dict[str, dict]:
    with open(DATA / "games.toml", "rb") as f:
        return tomllib.load(f).get("games", {})


@cache
def _anticheat_file() -> dict:
    try:
        return json.loads((DATA / "anticheat.json").read_text())
    except (OSError, ValueError):
        return {}


def is_native(appid: str) -> bool:
    """Есть Linux-версия (по заметкам games.toml или AreWeAntiCheatYet)."""
    ac = anticheat_db().get(appid)
    return bool(notes_db().get(appid, {}).get("native") or (ac and ac.get("native")))


def anticheat_db() -> dict[str, dict]:
    """{steam appid: запись AreWeAntiCheatYet}."""
    return _anticheat_file().get("games", {})


def normalize_name(name: str) -> str:
    """Как в scripts/update_anticheat.py: без регистра, ™®© и знаков препинания."""
    return re.sub(r"[^\w]+", " ", re.sub(r"[™®©]", "", name.lower())).strip()


def anticheat_by_name(name: str) -> dict | None:
    return _anticheat_file().get("by_name", {}).get(normalize_name(name))
