"""Запись параметров запуска в Steam (userdata/<id>/config/localconfig.vdf).

Это единственное место, где программа меняет файлы Steam, и только по кнопке пользователя.
Правила:
  - Steam должен быть закрыт: он держит настройки в памяти и при выходе перезапишет файл;
  - файл правится «точечно»: меняется одна строка LaunchOptions, остальное остаётся байт в байт;
  - перед записью сохраняется копия файла, а в журнал — старое значение, чтобы можно было откатить.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from doctor import vdf

log = logging.getLogger("doctor.steamcfg")

APPS_PATH = ("userlocalconfigstore", "software", "valve", "steam", "apps")
MAX_BACKUPS = 20


class SteamConfigError(Exception):
    pass


def localconfig_path(root: Path) -> Path | None:
    """localconfig.vdf последнего активного пользователя Steam."""
    configs = sorted((root / "userdata").glob("*/config/localconfig.vdf"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    return configs[0] if configs else None


def steam_running() -> bool:
    """Есть ли процесс steam (обычный или из Flatpak — у обоих comm = steam)."""
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() == "steam":
                return True
        except OSError:
            continue
    return False


# ---------------- точечная правка текста ----------------

@dataclass
class _Layout:
    blocks: dict[tuple, tuple[int, int]]   # путь блока -> (позиция «{», позиция «}»)
    values: dict[tuple, tuple[int, int]]   # путь ключа -> (начало, конец) значения в кавычках


def _layout(text: str) -> _Layout:
    blocks, values = {}, {}
    path: list[str] = []
    opens: list[int] = []
    key: str | None = None
    for m in vdf._TOKEN.finditer(text):
        if m.group(1) is not None or m.group(3) is not None:
            val = m.group(1) if m.group(1) is not None else m.group(3)
            if key is None:
                key = val.lower()
            else:
                values.setdefault((*path, key), m.span())
                key = None
        elif m.group(2) == "{":
            if key is None:
                raise vdf.VDFError("«{» без ключа")
            path.append(key)
            opens.append(m.start())
            key = None
        elif m.group(2) == "}":
            if not path:
                raise vdf.VDFError("лишняя «}»")
            blocks.setdefault(tuple(path), (opens.pop(), m.start()))
            path.pop()
    if path:
        raise vdf.VDFError("не закрыта «{»")
    return _Layout(blocks, values)


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def _indent(text: str, pos: int) -> str:
    start = _line_start(text, pos)
    return re.match(r"[ \t]*", text[start:pos])[0]


def set_launch_options(text: str, appid: str, value: str | None) -> str:
    """Новый текст файла: у игры appid параметры запуска value (None — убрать строку)."""
    lay = _layout(text)
    app = (*APPS_PATH, appid)
    key = (*app, "launchoptions")
    if key in lay.values:
        start, end = lay.values[key]
        if value is not None:
            return text[:start] + _quote(value) + text[end:]
        line = _line_start(text, start)
        nl = text.find("\n", end)
        return text[:line] + text[nl + 1 if nl != -1 else len(text):]
    if value is None:
        return text
    if app in lay.blocks:
        close = lay.blocks[app][1]
        ind = _indent(text, close)
        pos = _line_start(text, close)
        return text[:pos] + f'{ind}\t"LaunchOptions"\t\t{_quote(value)}\n' + text[pos:]
    if APPS_PATH not in lay.blocks:
        raise SteamConfigError("в localconfig.vdf нет раздела apps")
    close = lay.blocks[APPS_PATH][1]
    ind = _indent(text, close) + "\t"
    pos = _line_start(text, close)
    block = f'{ind}"{appid}"\n{ind}{{\n{ind}\t"LaunchOptions"\t\t{_quote(value)}\n{ind}}}\n'
    return text[:pos] + block + text[pos:]


def read_launch_options(text: str, appid: str) -> str | None:
    apps = vdf.loads(text)
    for k in APPS_PATH:
        apps = apps.get(k, {})
    app = apps.get(appid)
    return app.get("launchoptions") if isinstance(app, dict) else None


# ---------------- копии и журнал ----------------

def backups_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")
    return Path(base) / "linux-gamer-doctor" / "backups"


def _journal_path(directory: Path) -> Path:
    return directory / "launch_options.json"


def load_journal(directory: Path | None = None) -> list[dict]:
    try:
        data = json.loads(_journal_path(directory or backups_dir()).read_text())
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_journal(entries: list[dict], directory: Path) -> None:
    _journal_path(directory).write_text(json.dumps(entries[-200:], ensure_ascii=False, indent=1))


def last_change(appid: str, directory: Path | None = None) -> dict | None:
    """Последняя запись журнала по игре — для кнопки «Вернуть как было»."""
    for entry in reversed(load_journal(directory)):
        if entry.get("appid") == appid:
            return entry
    return None


def write(config: Path, appid: str, value: str | None, *, directory: Path | None = None,
          check_running: bool = True, undo: bool = False) -> str | None:
    """Записывает параметры запуска игры. Возвращает прежнее значение.

    Бросает SteamConfigError, если Steam запущен или файл не удалось разобрать/записать.
    """
    if check_running and steam_running():
        raise SteamConfigError("steam_running")
    directory = directory or backups_dir()
    try:
        text = config.read_text()
        old = read_launch_options(text, appid)
        new_text = set_launch_options(text, appid, value)
        if read_launch_options(new_text, appid) != value:  # проверяем себя, прежде чем писать
            raise SteamConfigError("после правки значение не совпало")
    except vdf.VDFError as e:
        raise SteamConfigError(f"localconfig.vdf не разобрать: {e}") from None
    except OSError as e:
        raise SteamConfigError(str(e)) from None

    try:
        directory.mkdir(parents=True, exist_ok=True)
        backup = directory / f"localconfig-{config.parent.parent.name}-{time.strftime('%Y%m%d-%H%M%S')}.vdf"
        shutil.copy2(config, backup)
        for extra in sorted(directory.glob("localconfig-*.vdf"))[:-MAX_BACKUPS]:
            extra.unlink()
        fd, tmp = tempfile.mkstemp(dir=config.parent, prefix=".localconfig-", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(new_text)
        shutil.copymode(config, tmp)
        os.replace(tmp, config)
    except OSError as e:
        raise SteamConfigError(str(e)) from None

    journal = load_journal(directory)
    journal.append({"time": time.time(), "file": str(config), "appid": appid, "old": old, "new": value,
                    "backup": str(backup), "undo": undo})
    _save_journal(journal, directory)
    log.info("launch options %s: %r -> %r (backup %s)", appid, old, value, backup)
    return old
