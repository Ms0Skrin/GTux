#!/usr/bin/env python3
"""Обновляет снимок базы AreWeAntiCheatYet (MIT) в doctor/data/anticheat.json.

Запускают разработчики перед релизом; самой программе интернет не нужен.
    python scripts/update_anticheat.py
"""

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

URL = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
OUT = Path(__file__).resolve().parent.parent / "doctor" / "data" / "anticheat.json"


def main() -> int:
    with urllib.request.urlopen(URL, timeout=30) as resp:
        games = json.load(resp)
    snapshot = {}
    for g in games:
        appid = (g.get("storeIds") or {}).get("steam")
        if not appid:
            continue  # без Steam appid сопоставить с установленной игрой не сможем
        snapshot[str(appid)] = {
            "name": g.get("name", ""),
            "status": g.get("status", ""),
            "native": bool(g.get("native")),
            "anticheats": g.get("anticheats", []),
            "updated": g.get("dateChanged") or "",
        }
    data = {
        "source": "https://areweanticheatyet.com (MIT License, (c) AreWeAntiCheatYet contributors)",
        "fetched": date.today().isoformat(),
        "games": dict(sorted(snapshot.items(), key=lambda kv: int(kv[0]))),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(snapshot)} игр со Steam appid -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
