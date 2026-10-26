"""Группа 8: игровые утилиты — gamemode, MangoHud, gamescope и их 32-битные части."""

from __future__ import annotations

from doctor import packages
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result
from doctor.system import which

GROUP = "tools"

# id: (программа в PATH, компонент, 32-битный компонент или None)
TOOLS = {
    "gamemode": ("gamemoderun", "gamemode", "lib32_gamemode"),
    "mangohud": ("mangohud", "mangohud", "lib32_mangohud"),
    "gamescope": ("gamescope", "gamescope", None),
}

# Утилиты, которые не всем нужны: не предлагаем их в автоустановке по умолчанию.
OPTIONAL = {"gamescope"}


def _make_check(tool_id: str):
    binary, comp, comp32 = TOOLS[tool_id]

    @check(tool_id)
    def _check(ctx: Context):
        main = packages.component(ctx, comp) or []
        lib32 = (packages.component(ctx, comp32) or []) if comp32 else []
        if not which(binary):
            fix = packages.fix_for(ctx, main + lib32)
            if tool_id in OPTIONAL:
                fix.pop("packages", None)  # команду покажем, но в --fix не включаем
            return result(GROUP, tool_id, Status.WARN, value=t("common.not_installed"),
                          hint=t(f"tools.{tool_id}.hint"), **fix)
        value = t("tools.found")
        if main:
            versions = packages.query(ctx, main + lib32)
            if versions.get(main[0]):
                value = packages.strip_version(versions[main[0]])
            missing32 = [p for p in lib32 if not versions.get(p)]
            if missing32:
                return result(GROUP, tool_id, Status.WARN, value=value,
                              hint=t("tools.no32_hint", pkg32=", ".join(missing32)),
                              **packages.fix_for(ctx, missing32))
        return result(GROUP, tool_id, Status.OK, value=value)

    return _check


CHECKS = [_make_check(tool_id) for tool_id in TOOLS]
