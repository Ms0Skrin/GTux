"""Данные об играх: установленные игры Steam, их настройки и база заметок.

Источники:
  - steamapps/appmanifest_*.acf — какие игры установлены;
  - config/config.vdf (CompatToolMapping) — какой Proton выбран для игры;
  - userdata/<id>/config/localconfig.vdf (LaunchOptions) — параметры запуска;
  - doctor/data/games.toml — ручные заметки с источниками;
  - doctor/data/anticheat.json — снимок AreWeAntiCheatYet.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from doctor import vdf

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
    configs = sorted((root / "userdata").glob("*/config/localconfig.vdf"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    if not configs:
        return {}
    apps = (_load_vdf(configs[0]).get("userlocalconfigstore", {}).get("software", {})
            .get("valve", {}).get("steam", {}).get("apps", {}))
    return {appid: v["launchoptions"] for appid, v in apps.items()
            if isinstance(v, dict) and v.get("launchoptions", "").strip()}


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


def anticheat_db() -> dict[str, dict]:
    """{steam appid: запись AreWeAntiCheatYet}."""
    return _anticheat_file().get("games", {})


def normalize_name(name: str) -> str:
    """Как в scripts/update_anticheat.py: без регистра, ™®© и знаков препинания."""
    return re.sub(r"[^\w]+", " ", re.sub(r"[™®©]", "", name.lower())).strip()


def anticheat_by_name(name: str) -> dict | None:
    return _anticheat_file().get("by_name", {}).get(normalize_name(name))
