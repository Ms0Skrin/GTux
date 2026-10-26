"""История проверок: что изменилось с прошлого раза.

Каждая проверка сохраняется в ~/.local/state/gtux/history/ (файлы программы,
система не меняется). Храним последние MAX_FILES запусков.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from gtux import __version__, paths
from gtux.models import CheckResult, Status

MAX_FILES = 30

# Проверки, у которых значение — версия (не зависит от языка), поэтому его изменение показываем.
TRACK_VALUES = {
    "distro.kernel", "gpu.nvidia_version", "gpu.mesa_version", "vulkan.loader",
    "multilib.nvidia_match", "tools.gamemode", "tools.mangohud", "tools.gamescope",
}


def history_dir() -> Path:
    return paths.state_dir() / "history"


@dataclass
class Change:
    id: str
    title: str
    kind: str                 # "status" | "value" | "added" | "removed"
    old: str = ""
    new: str = ""
    new_status: Status | None = None


def save(results: list[CheckResult], directory: Path | None = None) -> Path | None:
    directory = directory or history_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = directory / f"{stamp}.json"
        data = {"time": time.time(), "version": __version__,
                "results": [{"id": r.id, "title": r.title, "status": r.status.value, "value": r.value}
                            for r in results]}
        path.write_text(json.dumps(data, ensure_ascii=False))
        for old in sorted(directory.glob("*.json"))[:-MAX_FILES]:
            old.unlink()
        return path
    except OSError:
        return None  # не смогли сохранить историю — проверка от этого не хуже


def load_latest(directory: Path | None = None) -> dict | None:
    directory = directory or history_dir()
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    for f in reversed(files):
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            continue
    return None


def diff(previous: dict | None, results: list[CheckResult]) -> list[Change]:
    if not previous:
        return []
    old = {r["id"]: r for r in previous.get("results", [])}
    new = {r.id: r for r in results}
    changes = []
    for rid, r in new.items():
        before = old.get(rid)
        if before is None:
            changes.append(Change(rid, r.title, "added", new_status=r.status))
            continue
        if before["status"] != r.status.value:
            changes.append(Change(rid, r.title, "status", before["status"], r.status.value, r.status))
        elif rid in TRACK_VALUES and before["value"] != r.value:
            changes.append(Change(rid, r.title, "value", before["value"], r.value, r.status))
    for rid, before in old.items():
        if rid not in new:
            changes.append(Change(rid, before["title"], "removed", before["status"]))
    return changes
