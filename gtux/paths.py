"""Папки программы по XDG: ~/.cache/gtux, ~/.local/state/gtux, ~/.config/gtux.

До версии 0.5 программа называлась linux-gamer-doctor. Если есть старая папка, а новой ещё нет,
старая переезжает на новое место (история, база знаний и копии файлов Steam не теряются)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

NAME = "gtux"
OLD_NAME = "linux-gamer-doctor"


def _app_dir(env: str, default: str) -> Path:
    base = Path(os.environ.get(env) or Path.home() / default)
    new, old = base / NAME, base / OLD_NAME
    if old.is_dir() and not new.exists():
        try:
            old.rename(new)
        except OSError as e:
            logging.getLogger("gtux.paths").warning("cannot move %s to %s: %s", old, new, e)
            return old  # не получилось — продолжаем пользоваться старой
    return new


def cache_dir() -> Path:
    return _app_dir("XDG_CACHE_HOME", ".cache")


def state_dir() -> Path:
    return _app_dir("XDG_STATE_HOME", ".local/state")


def config_dir() -> Path:
    return _app_dir("XDG_CONFIG_HOME", ".config")
