"""Демо-режим окна (GTUX_GUI_DEMO=1): к настоящим результатам добавляются выдуманные
проблемы, чтобы увидеть все цвета и диалог исправления. Для скриншотов и разработки."""

from __future__ import annotations

from gtux.i18n import t
from gtux.models import Action, CheckResult, Context, Status
from gtux.packages import Pacman


def add_demo_problems(results: list[CheckResult], ctx: Context) -> tuple[list[CheckResult], Context]:
    demo = [
        CheckResult("vulkan.icd_demo", "vulkan", t("vulkan.icd.title") + " (AMD)", Status.FAIL,
                    value=t("vulkan.icd.none"),
                    hint=t("vulkan.icd.missing_hint", vendors="AMD") + " " +
                    t("vulkan.icd.packages", packages="vulkan-radeon"),
                    fix="sudo pacman -S --needed vulkan-radeon", packages=["vulkan-radeon"]),
        CheckResult("tools.gamescope", "tools", t("tools.gamescope.title"), Status.WARN,
                    value=t("common.not_installed"), hint=t("tools.gamescope.hint"),
                    fix="sudo pacman -S --needed gamescope"),
        CheckResult("tuning.max_map_count", "tuning", t("tuning.max_map_count.title"), Status.WARN,
                    value="65530", hint=t("tuning.max_map_count.low_hint", good=1048576),
                    fix="echo 'vm.max_map_count = 1048576' | sudo tee /etc/sysctl.d/80-gamecompatibility.conf",
                    actions=[Action("sysctl", "/etc/sysctl.d/80-gamecompatibility.conf", "vm.max_map_count = 1048576")]),
        CheckResult("disks.demo", "disks", t("disks.library.title", path="/media/usb"), Status.UNKNOWN,
                    value="exfat", error="PermissionError: [Errno 13] /media/usb"),
    ]
    by_group: dict[str, list[CheckResult]] = {}
    for r in results + demo:
        by_group.setdefault(r.group, []).append(r)
    merged = [r for g in dict.fromkeys(r.group for r in results) for r in by_group[g]]
    if ctx.package_manager is None:
        ctx.package_manager = Pacman()
    return merged, ctx
