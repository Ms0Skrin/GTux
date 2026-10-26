"""Группа 7: Proton — официальные версии от Valve и сторонние сборки (GE, CachyOS и др.)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gtux import vdf
from gtux.i18n import t
from gtux.models import Context, Status
from gtux.runner import check, result

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


@dataclass
class CompatTool:
    name: str                 # отображаемое имя
    internal: list[str]       # внутренние имена (их Steam пишет в config.vdf), в нижнем регистре
    path: Path


def custom_tools(dirs: list[Path]) -> list[CompatTool]:
    """Сборки из compatibilitytools.d. Имена берём из compatibilitytool.vdf."""
    tools = []
    for d in dirs:
        if not d.is_dir():
            continue
        for tool in sorted(d.iterdir()):
            manifest = tool / "compatibilitytool.vdf"
            if not manifest.is_file():
                continue
            name, internal = tool.name, []
            try:
                compat = vdf.loads(manifest.read_text(errors="replace"))
                entries = compat.get("compatibilitytools", {}).get("compat_tools", {})
                for key, entry in entries.items():
                    internal.append(key)
                    if isinstance(entry, dict) and entry.get("display_name") and name == tool.name:
                        name = entry["display_name"]
            except (OSError, vdf.VDFError):
                pass  # имя папки — тоже нормальное название
            tools.append(CompatTool(name, internal, tool))
    return tools


def installed_tool_names(ctx: Context) -> set[str]:
    """Внутренние имена всех установленных сторонних сборок (нижний регистр)."""
    return {n for tool in custom_tools(_compat_dirs(ctx)) for n in tool.internal}


def installed_variants(ctx: Context) -> dict[str, list[str]]:
    """Установленные сборки по видам ProtonDB (official, experimental, ge, cachyos)."""
    from gtux.knowledge import installed_variants as split
    names, _ = official_protons(ctx.steam_libraries)
    return split(names, [tool.name for tool in custom_tools(_compat_dirs(ctx))])


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
    names = list(dict.fromkeys(tool.name for tool in tools))
    has_ge = any(GE_PATTERN.search(tool.name) or GE_PATTERN.search(tool.path.name) for tool in tools)
    value = ", ".join(names) or t("proton.custom.none")
    if not has_ge:
        return result(GROUP, "custom", Status.WARN, value=value, hint=t("proton.custom.no_ge_hint"))
    return result(GROUP, "custom", Status.OK, value=value)


CHECKS = [check_official, check_custom]
