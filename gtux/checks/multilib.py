"""Группа 4: 32-битная поддержка. Steam и многие игры (особенно старые) 32-битные.

Arch: репозиторий [multilib]. Debian/Ubuntu: архитектура i386. Fedora: пакеты .i686 доступны всегда.
"""

from __future__ import annotations

import re

from gtux import packages
from gtux.checks.gpu import GOOD_DRIVERS, VENDOR_NAMES
from gtux.i18n import t
from gtux.models import Context, Status
from gtux.packages import Apt, Dnf, Pacman
from gtux.runner import check, result
from gtux.system import read_text

GROUP = "multilib"

PACMAN_CONF = "/etc/pacman.conf"

LIB32_BY_VENDOR = {"nvidia": "lib32_nvidia", "amd": "lib32_amd", "intel": "lib32_intel"}

# Команды, включающие 32-битную архитектуру (для показа и для --fix).
ENABLE_I386 = "sudo dpkg --add-architecture i386 && sudo apt update"


def multilib_enabled(conf_text: str) -> bool:
    """Есть ли незакомментированный раздел [multilib] в pacman.conf."""
    return any(re.fullmatch(r"\[multilib\]", line.split("#", 1)[0].strip())
               for line in conf_text.splitlines())


@check("repo")
def check_repo(ctx: Context):
    pm = ctx.package_manager
    if isinstance(pm, Pacman):
        conf = read_text(PACMAN_CONF)
        if conf is None:
            return result(GROUP, "repo", Status.UNKNOWN, error=t("multilib.repo.no_conf", path=PACMAN_CONF))
        ctx.multilib_enabled = multilib_enabled(conf)
        if not ctx.multilib_enabled:
            return result(GROUP, "repo", Status.FAIL, value=t("multilib.repo.disabled"),
                          hint=t("multilib.repo.disabled_hint", path=PACMAN_CONF),
                          fix=f"sudoedit {PACMAN_CONF} && sudo pacman -Syu")
        return result(GROUP, "repo", Status.OK, value=t("multilib.repo.enabled"))
    if isinstance(pm, Apt):
        ctx.multilib_enabled = pm.i386_enabled()
        if not ctx.multilib_enabled:
            return result(GROUP, "repo", Status.FAIL, value=t("multilib.repo.i386_disabled"),
                          hint=t("multilib.repo.i386_hint"), fix=ENABLE_I386)
        return result(GROUP, "repo", Status.OK, value=t("multilib.repo.i386_enabled"))
    if isinstance(pm, Dnf):
        ctx.multilib_enabled = True
        return result(GROUP, "repo", Status.OK, value=t("multilib.repo.fedora"))
    return result(GROUP, "repo", Status.UNKNOWN, value=t("multilib.unsupported"))


@check("packages")
def check_packages(ctx: Context):
    if ctx.package_manager is None:
        return []  # причину уже показала проверка repo
    vendors = sorted({g.vendor for g in ctx.gpus
                      if g.vendor in LIB32_BY_VENDOR and g.driver in GOOD_DRIVERS[g.vendor]})
    wanted = list(packages.component(ctx, "lib32_vulkan_loader") or [])
    unknown = []
    for v in vendors:
        names = packages.component(ctx, LIB32_BY_VENDOR[v])
        if names is None:
            unknown.append(VENDOR_NAMES[v])
        else:
            wanted += [n for n in names if n not in wanted]
    if not wanted:
        return result(GROUP, "packages", Status.UNKNOWN, value=t("multilib.unsupported"))

    versions = packages.query(ctx, wanted)
    missing = [p for p in wanted if versions[p] is None]
    installed = [p for p in wanted if versions[p] is not None]
    note = "\n" + t("multilib.packages.unknown_vendor", vendors=", ".join(unknown)) if unknown else ""
    if missing:
        hint = t("multilib.packages.missing_hint")
        if ctx.multilib_enabled is False:
            hint += " " + t("multilib.packages.enable_first")
        return result(GROUP, "packages", Status.FAIL,
                      value=t("multilib.packages.missing", packages=", ".join(missing)) + note,
                      hint=hint, **packages.fix_for(ctx, missing))
    vendor_names = ", ".join(VENDOR_NAMES[v] for v in vendors)
    value = ", ".join(installed) + (f" ({vendor_names})" if vendor_names else "") + note
    return result(GROUP, "packages", Status.OK, value=value)


@check("nvidia_match")
def check_nvidia_match(ctx: Context):
    """64- и 32-битная части драйвера NVIDIA должны быть одной версии (проверяем на Arch)."""
    if not isinstance(ctx.package_manager, Pacman) or \
            not any(g.vendor == "nvidia" and g.driver == "nvidia" for g in ctx.gpus):
        return []
    v = packages.query(ctx, ["nvidia-utils", "lib32-nvidia-utils"])
    v64, v32 = v["nvidia-utils"], v["lib32-nvidia-utils"]
    if not v64 or not v32:
        return []  # отсутствие пакета уже показано выше
    s64, s32 = packages.strip_version(v64), packages.strip_version(v32)
    if s64 != s32:
        return result(GROUP, "nvidia_match", Status.FAIL,
                      value=t("multilib.nvidia_match.differ", v64=s64, v32=s32),
                      hint=t("multilib.nvidia_match.differ_hint"), fix="sudo pacman -Syu")
    return result(GROUP, "nvidia_match", Status.OK, value=s64)


CHECKS = [check_repo, check_packages, check_nvidia_match]
