"""Безопасные помощники для чтения системы. Только чтение, без shell и без sudo."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("doctor.system")

DEFAULT_TIMEOUT = 15  # секунд; vulkaninfo на некоторых системах думает долго


class CommandError(Exception):
    """Команду не удалось выполнить: её нет, она зависла или упала."""


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], timeout: int = DEFAULT_TIMEOUT) -> CmdResult:
    """Запускает команду со списком аргументов (без shell) и возвращает вывод.

    Ненулевой код возврата не считается ошибкой: многие утилиты так отвечают «нет».
    """
    if which(cmd[0]) is None:
        log.debug("not found: %s", cmd[0])
        raise CommandError(f"команда «{cmd[0]}» не найдена")
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Английская локаль, чтобы вывод утилит было проще разбирать.
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired:
        log.warning("timeout %ss: %s", timeout, cmd)
        raise CommandError(f"«{' '.join(cmd)}» не ответила за {timeout} с") from None
    except OSError as e:
        log.warning("failed to start %s: %s", cmd, e)
        raise CommandError(f"не удалось запустить «{cmd[0]}»: {e}") from None
    log.debug("run %s -> rc=%s in %.2fs%s", cmd, proc.returncode, time.monotonic() - started,
              f"; stderr: {proc.stderr.strip()[-300:]}" if proc.returncode and proc.stderr.strip() else "")
    return CmdResult(proc.returncode, proc.stdout, proc.stderr)


def read_text(path: str | Path) -> str | None:
    """Читает файл целиком; None, если файла нет или нет доступа."""
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return None
