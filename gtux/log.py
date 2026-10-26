"""Отладочный журнал: ~/.local/state/gtux/gtux.log

Нужен, чтобы разбираться с багами: что запускали, сколько длились проверки, какие команды
вызывались и с каким кодом, полный текст исключений. Остаётся только на компьютере пользователя.
"""

from __future__ import annotations

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from gtux import __version__, paths

logger = logging.getLogger("gtux")

MAX_BYTES = 1024 * 1024
BACKUPS = 3


def log_path() -> Path:
    return paths.state_dir() / "gtux.log"


def setup(debug: bool = False, argv: list[str] | None = None) -> Path | None:
    """Включает журнал. В файл пишется всё (DEBUG); с --debug — ещё и в stderr."""
    if logger.handlers:
        return log_path()  # уже настроен (например, окно пересоздали)
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except OSError as e:
        print(f"gtux: log file unavailable ({e})", file=sys.stderr)
        path = None
    if debug:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(fmt)
        logger.addHandler(console)
    logger.info("=== start v%s, python %s, kernel %s, argv=%s", __version__,
                platform.python_version(), platform.release(), argv if argv is not None else sys.argv[1:])
    return path
