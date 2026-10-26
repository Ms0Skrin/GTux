"""Безопасные помощники для чтения системы. Только чтение, без shell и без sudo."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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
        raise CommandError(f"команда «{cmd[0]}» не найдена")
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
        raise CommandError(f"«{' '.join(cmd)}» не ответила за {timeout} с") from None
    except OSError as e:
        raise CommandError(f"не удалось запустить «{cmd[0]}»: {e}") from None
    return CmdResult(proc.returncode, proc.stdout, proc.stderr)


def read_text(path: str | Path) -> str | None:
    """Читает файл целиком; None, если файла нет или нет доступа."""
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return None
