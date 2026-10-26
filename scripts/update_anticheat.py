#!/usr/bin/env python3
"""Обновляет снимок базы AreWeAntiCheatYet (MIT) в gtux/data/anticheat.json.

Запускают разработчики перед релизом; самой программе интернет не нужен.
    python scripts/update_anticheat.py
"""

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

URL = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
OUT = Path(__file__).resolve().parent.parent / "gtux" / "data" / "anticheat.json"


def normalize(name: str) -> str:
    """Название для сравнения: без регистра, ™®© и знаков препинания. Дублируется в gtux/gamedb.py."""
    return re.sub(r"[^\w]+", " ", re.sub(r"[™®©]", "", name.lower())).strip()


def entry(g: dict) -> dict:
    return {
        "name": g.get("name", ""),
        "status": g.get("status", ""),
        "native": bool(g.get("native")),
        "anticheats": g.get("anticheats", []),
        "updated": g.get("dateChanged") or "",
    }


def main() -> int:
    with urllib.request.urlopen(URL, timeout=30) as resp:
        games = json.load(resp)
    snapshot, by_name = {}, {}
    for g in games:
        appid = (g.get("storeIds") or {}).get("steam")
        if appid:
            snapshot[str(appid)] = entry(g)
        if g.get("name"):
            # Для Heroic/Lutris/Faugus appid нет — ищем по точному совпадению названия.
            by_name.setdefault(normalize(g["name"]), entry(g))
    data = {
        "source": "https://areweanticheatyet.com (MIT License, (c) AreWeAntiCheatYet contributors)",
        "fetched": date.today().isoformat(),
        "games": dict(sorted(snapshot.items(), key=lambda kv: int(kv[0]))),
        "by_name": dict(sorted(by_name.items())),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(snapshot)} игр со Steam appid, {len(by_name)} по названию -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
