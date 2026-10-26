"""Группа 7: Proton — официальные версии от Valve и сторонние сборки (GE, CachyOS и др.)."""

from __future__ import annotations

import re
from pathlib import Path

from doctor import vdf
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result

GROUP = "proton"

# Системные папки, куда пакеты дистрибутива кладут сборки Proton.
SYSTEM_COMPAT_DIRS = [Path("/usr/share/steam/compatibilitytools.d"),
                      Path("/usr/local/share/steam/compatibilitytools.d")]

GE_PATTERN = re.compile(r"GE-Proton|Proton-GE", re.IGNORECASE)


def official_protons(libraries: list[Path]) -> tuple[list[str], list[str]]:
    """(установленные, остатки): папки steamapps/common/Proton* со скриптом proton и без него."""
    installed, leftovers = set(), set()
    for lib in libraries:
        common = lib / "steamapps" / "common"
        if common.is_dir():
            for p in common.glob("Proton*"):
                (installed if (p / "proton").is_file() else leftovers).add(p.name)
    return sorted(installed), sorted(leftovers - installed)


def custom_tools(dirs: list[Path]) -> list[tuple[str, Path]]:
    """[(отображаемое имя, папка)] из compatibilitytools.d. Имя берём из compatibilitytool.vdf."""
    tools = []
    for d in dirs:
        if not d.is_dir():
            continue
        for tool in sorted(d.iterdir()):
            manifest = tool / "compatibilitytool.vdf"
            if not manifest.is_file():
                continue
            name = tool.name
            try:
                compat = vdf.loads(manifest.read_text(errors="replace"))
                entries = compat.get("compatibilitytools", {}).get("compat_tools", {})
                for entry in entries.values():
                    if isinstance(entry, dict) and entry.get("display_name"):
                        name = entry["display_name"]
                        break
            except (OSError, vdf.VDFError):
                pass  # имя папки — тоже нормальное название
            tools.append((name, tool))
    return tools


def _compat_dirs(ctx: Context) -> list[Path]:
    dirs = [root / "compatibilitytools.d" for _, root in ctx.steam_roots]
    return dirs + SYSTEM_COMPAT_DIRS


@check("official")
def check_official(ctx: Context):
    if not ctx.steam_roots:
        return result(GROUP, "official", Status.UNKNOWN, value=t("proton.no_steam"))
    names, leftovers = official_protons(ctx.steam_libraries)
    value = ", ".join(names) or t("proton.official.none")
    if leftovers:
        value += "\n" + t("proton.official.leftovers", names=", ".join(leftovers))
    if not names:
        return result(GROUP, "official", Status.WARN, value=value, hint=t("proton.official.none_hint"))
    return result(GROUP, "official", Status.OK, value=value)


@check("custom")
def check_custom(ctx: Context):
    if not ctx.steam_roots:
        return []
    tools = custom_tools(_compat_dirs(ctx))
    names = list(dict.fromkeys(name for name, _ in tools))
    has_ge = any(GE_PATTERN.search(name) or GE_PATTERN.search(path.name) for name, path in tools)
    value = ", ".join(names) or t("proton.custom.none")
    if not has_ge:
        return result(GROUP, "custom", Status.WARN, value=value, hint=t("proton.custom.no_ge_hint"))
    return result(GROUP, "custom", Status.OK, value=value)


CHECKS = [check_official, check_custom]
