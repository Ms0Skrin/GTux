"""Группа 1: дистрибутив, ядро, пакетный менеджер."""

from __future__ import annotations

import platform
import re

from gtux import packages
from gtux.i18n import t
from gtux.models import Context, Status
from gtux.runner import check, result
from gtux.system import which

GROUP = "distro"

# futex_waitv появился в ядре 5.16; на нём держится fsync в Wine/Proton.
MIN_KERNEL_FSYNC = (5, 16)


@check("os")
def check_os(ctx: Context):
    try:
        info = platform.freedesktop_os_release()
    except OSError as e:
        return result(GROUP, "os", Status.UNKNOWN, value=t("distro.os.no_file"), error=str(e))
    ctx.distro_id = info.get("ID", "")
    ctx.distro_like = info.get("ID_LIKE", "").split()
    name = info.get("PRETTY_NAME") or info.get("NAME") or ctx.distro_id
    if ctx.distro_like:
        name += t("distro.os.based_on", base=", ".join(ctx.distro_like))
    return result(GROUP, "os", Status.OK, value=name)


@check("kernel")
def check_kernel(ctx: Context):
    release = platform.release()
    m = re.match(r"(\d+)\.(\d+)", release)
    if not m:
        return result(GROUP, "kernel", Status.UNKNOWN, value=release,
                      error=t("distro.kernel.unparsed"))
    if (int(m[1]), int(m[2])) < MIN_KERNEL_FSYNC:
        return result(GROUP, "kernel", Status.WARN, value=release,
                      hint=t("distro.kernel.old_hint"))
    return result(GROUP, "kernel", Status.OK, value=release)


@check("package_manager")
def check_package_manager(ctx: Context):
    ctx.package_manager = packages.detect([ctx.distro_id, *ctx.distro_like])
    if ctx.package_manager is None:
        # Узнаём хотя бы имя, чтобы честно сказать, что не поддерживаем.
        found = next((pm for pm in ("zypper", "xbps-install", "emerge", "apk", "nix-env")
                      if which(pm)), None)
        return result(GROUP, "package_manager", Status.WARN,
                      value=found or t("distro.package_manager.none"),
                      hint=t("distro.package_manager.unsupported_hint"))
    value = ctx.package_manager.name
    helpers = [h for h in ("paru", "yay") if which(h)]
    if helpers:
        value += t("distro.package_manager.aur", helpers=", ".join(helpers))
    if which("flatpak"):
        value += t("distro.package_manager.flatpak")
    return result(GROUP, "package_manager", Status.OK, value=value)


CHECKS = [check_os, check_kernel, check_package_manager]
