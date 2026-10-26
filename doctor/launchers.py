"""Игры из сторонних лаунчеров: Heroic, Lutris, Faugus.

Только чтение их файлов. Форматы взяты из исходников лаунчеров:
  Heroic: src/backend/constants/paths.ts, storeManagers/*/constants.ts и electronStores.ts,
          src/common/types.ts (GameSettings, WineInstallation)
  Lutris: база pga.db (таблица games) и YAML-конфиги игр
  Faugus: faugus/path_manager.py (GAMES_JSON), класс Game в faugus/launcher.py
Если файл не того формата — пропускаем лаунчер, а не падаем: у пользователя может быть
другая версия лаунчера.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()

HEROIC_DIRS = [HOME / ".config/heroic", HOME / ".var/app/com.heroicgameslauncher.hgl/config/heroic"]
LUTRIS_DATA_DIRS = [HOME / ".local/share/lutris", HOME / ".var/app/net.lutris.Lutris/data/lutris"]
LUTRIS_CONFIG_DIRS = [HOME / ".config/lutris", HOME / ".var/app/net.lutris.Lutris/config/lutris"]
FAUGUS_GAMES = [HOME / ".local/share/faugus-launcher/games.json",
                HOME / ".var/app/io.github.Faugus.faugus-launcher/data/faugus-launcher/games.json"]


@dataclass
class ExternalGame:
    source: str                          # "Heroic (Epic)", "Lutris", "Faugus"…
    id: str
    name: str
    install_path: Path | None = None     # папка игры (или exe) — должна существовать
    windows: bool = True                 # запускается через Wine/Proton
    runner: str = ""                     # отображаемое имя Wine/Proton
    runner_path: Path | None = None      # путь, который должен существовать (если известен)
    runner_found: bool | None = None     # True/False — проверили сами; None — не знаем
    prefix: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    wrappers: list[str] = field(default_factory=list)  # gamemoderun, mangohud…


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except (OSError, ValueError):
        return None


def _path(value) -> Path | None:
    return Path(value).expanduser() if isinstance(value, str) and value.strip() else None


# ---------------- Heroic ----------------

def _heroic_settings(root: Path, app_name: str) -> dict:
    data = _read_json(root / "GamesConfig" / f"{app_name}.json") or {}
    return data.get(app_name, {}) if isinstance(data, dict) else {}


def _heroic_game(root: Path, store: str, app_name: str, title: str,
                 install_path, platform) -> ExternalGame:
    s = _heroic_settings(root, app_name)
    windows = str(platform or "windows").lower() == "windows"
    game = ExternalGame(f"Heroic ({store})", app_name, title or app_name,
                        install_path=_path(install_path), windows=windows)
    wine = s.get("wineVersion") or {}
    if windows and isinstance(wine, dict):
        game.runner = wine.get("name", "")
        game.runner_path = _path(wine.get("bin"))
        if game.runner_path:
            game.runner_found = game.runner_path.exists()
    game.prefix = _path(s.get("winePrefix")) if windows else None
    for item in s.get("enviromentOptions") or []:  # sic: так в исходниках Heroic
        if isinstance(item, dict) and item.get("key"):
            game.env[item["key"]] = str(item.get("value", ""))
    if s.get("useGameMode"):
        game.wrappers.append("gamemoderun")
    if s.get("showMangohud"):
        game.wrappers.append("mangohud")
    for w in s.get("wrapperOptions") or []:
        if isinstance(w, dict) and w.get("exe"):
            game.wrappers.append(Path(w["exe"]).name)
    return game


def heroic_games() -> list[ExternalGame]:
    games = []
    for root in HEROIC_DIRS:
        if not root.is_dir():
            continue
        # Epic (через legendary): {appName: {title, install_path, platform, ...}}
        legendary = _read_json(root / "legendaryConfig/legendary/installed.json") or {}
        for app, info in (legendary.items() if isinstance(legendary, dict) else []):
            if isinstance(info, dict) and not info.get("is_dlc"):
                games.append(_heroic_game(root, "Epic", app, info.get("title", ""),
                                          info.get("install_path"), info.get("platform")))
        # GOG: gog_store/installed.json -> {"installed": [{appName, install_path, platform}]}
        gog_titles = {g.get("app_name"): g.get("title") for g in
                      ((_read_json(root / "store_cache/gog_library.json") or {}).get("games") or [])
                      if isinstance(g, dict)}
        for info in (_read_json(root / "gog_store/installed.json") or {}).get("installed") or []:
            if isinstance(info, dict) and info.get("appName"):
                app = info["appName"]
                games.append(_heroic_game(root, "GOG", app, gog_titles.get(app, ""),
                                          info.get("install_path"), info.get("platform")))
        # Amazon (через nile): installed.json -> [{id, path}], названия в library.json
        nile_titles = {}
        for item in _read_json(root / "nile_config/nile/library.json") or []:
            product = item.get("product", {}) if isinstance(item, dict) else {}
            if product.get("id"):
                nile_titles[product["id"]] = product.get("title", "")
        for info in _read_json(root / "nile_config/nile/installed.json") or []:
            if isinstance(info, dict) and info.get("id"):
                games.append(_heroic_game(root, "Amazon", info["id"], nile_titles.get(info["id"], ""),
                                          info.get("path"), "windows"))
        # Добавленные вручную: sideload_apps/library.json -> {"games": [GameInfo]}
        for info in (_read_json(root / "sideload_apps/library.json") or {}).get("games") or []:
            if isinstance(info, dict) and info.get("is_installed") and info.get("app_name"):
                install = info.get("install") or {}
                games.append(_heroic_game(root, "sideload", info["app_name"], info.get("title", ""),
                                          info.get("folder_name") or install.get("executable"),
                                          install.get("platform")))
    return games


# ---------------- Lutris ----------------

def parse_simple_yaml(text: str) -> dict[str, dict[str, str]]:
    """Двухуровневый YAML Lutris-конфигов: «раздел:» и «  ключ: значение». Списки пропускаем."""
    data: dict[str, dict[str, str]] = {}
    section: dict[str, str] | None = None
    subsection: dict[str, str] | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith(("#", "- ")):
            continue
        indent = len(raw) - len(raw.lstrip())
        key, _, value = raw.strip().partition(":")
        value = value.strip().strip("'\"")
        if indent == 0:
            section = data.setdefault(key, {})
            subsection = None
        elif section is not None and indent <= 2:
            if value:
                section[key] = value
                subsection = None
            else:
                subsection = {}  # например system: env: — вложенный словарь
                section[key] = subsection  # type: ignore[assignment]
        elif subsection is not None:
            subsection[key] = value
    return data


def _lutris_wine_found(data_dir: Path, version: str) -> bool | None:
    if not version or version in ("system",):
        return None
    candidates = [data_dir / "runners/wine" / version,
                  HOME / ".local/share/Steam/compatibilitytools.d" / version,
                  HOME / ".steam/root/compatibilitytools.d" / version]
    return any(c.exists() for c in candidates)


def lutris_games() -> list[ExternalGame]:
    games = []
    for data_dir in LUTRIS_DATA_DIRS:
        db = data_dir / "pga.db"
        if not db.is_file():
            continue
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)  # только чтение
            rows = con.execute("SELECT slug, name, runner, directory, configpath "
                               "FROM games WHERE installed = 1").fetchall()
            con.close()
        except sqlite3.Error:
            continue
        for slug, name, runner, directory, configpath in rows:
            conf: dict = {}
            for conf_dir in [data_dir / "games", *[d / "games" for d in LUTRIS_CONFIG_DIRS]]:
                f = conf_dir / f"{configpath}.yml"
                if configpath and f.is_file():
                    conf = parse_simple_yaml(f.read_text(errors="replace"))
                    break
            game_conf = conf.get("game", {})
            windows = runner == "wine"
            game = ExternalGame("Lutris", slug or name, name or slug,
                                install_path=_path(directory) or _path(game_conf.get("exe")),
                                windows=windows)
            if windows:
                game.runner = conf.get("wine", {}).get("version", "")
                game.runner_found = _lutris_wine_found(data_dir, game.runner)
                game.prefix = _path(game_conf.get("prefix"))
            env = conf.get("system", {}).get("env")
            if isinstance(env, dict):
                game.env.update(env)
            if conf.get("system", {}).get("gamemode") in ("true", "True"):
                game.wrappers.append("gamemoderun")
            if conf.get("system", {}).get("mangohud") in ("true", "True"):
                game.wrappers.append("mangohud")
            games.append(game)
    return games


# ---------------- Faugus ----------------

def faugus_games() -> list[ExternalGame]:
    games = []
    for path in FAUGUS_GAMES:
        data = _read_json(path)
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            runner = str(item.get("runner") or "")
            if runner == "Steam":
                continue  # это ярлык на игру Steam — её уже проверили в Steam-разделе
            game = ExternalGame("Faugus", str(item.get("gameid") or item["title"]), item["title"],
                                install_path=_path(item.get("path")), windows=runner != "Linux",
                                runner=runner, prefix=_path(item.get("prefix")))
            for token in str(item.get("launch_arguments") or "").split():
                key, eq, value = token.partition("=")
                if eq and key.isidentifier():
                    game.env[key] = value
            if item.get("gamemode") is True:
                game.wrappers.append("gamemoderun")
            if item.get("mangohud") is True:
                game.wrappers.append("mangohud")
            games.append(game)
    return games


def all_games() -> list[ExternalGame]:
    return heroic_games() + lutris_games() + faugus_games()
