"""Короткая сводка JSON GTux для scripts/distro_test.sh: распознанная система, пакеты, план исправления."""
import json
import sys

d = json.load(sys.stdin)
print("  сводка:", d["summary"])
for r in d["results"]:
    if r["group"] in ("distro", "multilib", "steam", "tools", "apps", "vulkan") or r["status"] == "unknown":
        err = f"  [ошибка: {r['error']}]" if r.get("error") else ""
        print(f"  {r['status']:8} {r['title']}: {r['value'][:90]}{err}".replace("\n", " / "))
plan = d["fix_plan"]
for s in plan["steps"]:
    print("  исправить:", s["command"])
if plan["skipped"]:
    print("  пропущено:", plan["skipped"])
for s in plan["offers"]:
    print("  по желанию:", " && ".join([p["command"] for p in s["prereq"]] + [s["command"]]))
if plan.get("unavailable"):
    print("  недоступно в репозиториях:", plan["unavailable"])
