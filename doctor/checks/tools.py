"""Группа 8: игровые утилиты — gamemode, MangoHud, gamescope и их 32-битные части."""

from __future__ import annotations

from doctor import packages
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.packages import Pacman
from doctor.runner import check, result
from doctor.system import which

GROUP = "tools"

# id: (программа для поиска в PATH, пакет Arch, 32-битный пакет Arch или None)
TOOLS = {
    "gamemode": ("gamemoderun", "gamemode", "lib32-gamemode"),
    "mangohud": ("mangohud", "mangohud", "lib32-mangohud"),
    "gamescope": ("gamescope", "gamescope", None),
}


def _make_check(tool_id: str):
    binary, pkg, pkg32 = TOOLS[tool_id]

    @check(tool_id)
    def _check(ctx: Context):
        is_pacman = isinstance(ctx.package_manager, Pacman)
        hint = t(f"tools.{tool_id}.hint")
        if not which(binary):
            fix = ctx.package_manager.install_command([pkg] + ([pkg32] if pkg32 else [])) \
                if is_pacman else None
            return result(GROUP, tool_id, Status.WARN, value=t("common.not_installed"),
                          hint=hint, fix=fix)
        value = t("tools.found")
        if is_pacman:
            wanted = [pkg] + ([pkg32] if pkg32 else [])
            versions = packages.query(ctx, wanted)
            if versions.get(pkg):
                value = packages.strip_version(versions[pkg])
            if pkg32 and not versions.get(pkg32):
                return result(GROUP, tool_id, Status.WARN, value=value,
                              hint=t("tools.no32_hint", pkg32=pkg32),
                              fix=ctx.package_manager.install_command([pkg32]))
        return result(GROUP, tool_id, Status.OK, value=value)

    return _check


CHECKS = [_make_check(tool_id) for tool_id in TOOLS]
