"""Группа 4: 32-битная поддержка. Steam и многие игры (особенно старые) 32-битные."""

from __future__ import annotations

import re

from doctor import packages
from doctor.checks.gpu import GOOD_DRIVERS, VENDOR_NAMES
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.packages import Pacman
from doctor.runner import check, result
from doctor.system import read_text

GROUP = "multilib"

PACMAN_CONF = "/etc/pacman.conf"

# 32-битные пакеты Arch, нужные для каждого вендора (проверено по базе multilib).
LIB32_BY_VENDOR = {
    "nvidia": ["lib32-nvidia-utils"],
    "amd": ["lib32-mesa", "lib32-vulkan-radeon"],
    "intel": ["lib32-mesa", "lib32-vulkan-intel"],
}
LIB32_COMMON = ["lib32-vulkan-icd-loader"]


def multilib_enabled(conf_text: str) -> bool:
    """Есть ли незакомментированный раздел [multilib] в pacman.conf."""
    return any(re.fullmatch(r"\[multilib\]", line.split("#", 1)[0].strip())
               for line in conf_text.splitlines())


def _is_pacman(ctx: Context) -> bool:
    return isinstance(ctx.package_manager, Pacman)


@check("repo")
def check_repo(ctx: Context):
    if not _is_pacman(ctx):
        return result(GROUP, "repo", Status.UNKNOWN, value=t("multilib.only_arch"))
    conf = read_text(PACMAN_CONF)
    if conf is None:
        return result(GROUP, "repo", Status.UNKNOWN, error=t("multilib.repo.no_conf", path=PACMAN_CONF))
    ctx.multilib_enabled = multilib_enabled(conf)
    if not ctx.multilib_enabled:
        return result(GROUP, "repo", Status.FAIL, value=t("multilib.repo.disabled"),
                      hint=t("multilib.repo.disabled_hint", path=PACMAN_CONF),
                      fix=f"sudoedit {PACMAN_CONF} && sudo pacman -Syu")
    return result(GROUP, "repo", Status.OK, value=t("multilib.repo.enabled"))


@check("packages")
def check_packages(ctx: Context):
    if not _is_pacman(ctx):
        return []  # причину уже показала проверка repo
    vendors = sorted({g.vendor for g in ctx.gpus
                      if g.vendor in LIB32_BY_VENDOR and g.driver in GOOD_DRIVERS[g.vendor]})
    wanted = list(dict.fromkeys(LIB32_COMMON + [p for v in vendors for p in LIB32_BY_VENDOR[v]]))
    versions = packages.query(ctx, wanted)
    missing = [p for p in wanted if versions[p] is None]
    installed = [p for p in wanted if versions[p] is not None]
    if missing:
        hint = t("multilib.packages.missing_hint")
        if ctx.multilib_enabled is False:
            hint += " " + t("multilib.packages.enable_first")
        return result(GROUP, "packages", Status.FAIL,
                      value=t("multilib.packages.missing", packages=", ".join(missing)),
                      hint=hint, fix=ctx.package_manager.install_command(missing))
    vendor_names = ", ".join(VENDOR_NAMES[v] for v in vendors)
    value = ", ".join(installed) + (f" ({vendor_names})" if vendor_names else "")
    return result(GROUP, "packages", Status.OK, value=value)


@check("nvidia_match")
def check_nvidia_match(ctx: Context):
    """64- и 32-битная части драйвера NVIDIA должны быть одной версии."""
    if not _is_pacman(ctx) or not any(g.vendor == "nvidia" and g.driver == "nvidia" for g in ctx.gpus):
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
