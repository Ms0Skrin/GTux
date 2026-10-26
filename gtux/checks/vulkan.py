"""Группа 3: Vulkan. Без него не работают Proton/DXVK, то есть почти все игры из Windows."""

from __future__ import annotations

import re
from pathlib import Path

from gtux import packages
from gtux.checks.gpu import GOOD_DRIVERS, VENDOR_NAMES
from gtux.i18n import t
from gtux.models import Context, Status
from gtux.runner import check, result
from gtux.system import run, which

GROUP = "vulkan"

ICD_DIRS = [Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d")]

# Начало имени ICD-файла (описания Vulkan-драйвера) и компонент из gtux.pkgnames, который его ставит.
ICD_BY_VENDOR = {
    "nvidia": ("nvidia_icd", "vulkan_nvidia"),
    "amd": ("radeon_icd", "vulkan_amd"),
    "intel": ("intel_icd", "vulkan_intel"),
}


def _icd_files() -> list[str]:
    return sorted(p.name for d in ICD_DIRS if d.is_dir() for p in d.glob("*.json"))


@check("loader")
def check_loader(ctx: Context):
    names = packages.component(ctx, "vulkan_loader")
    if not names:
        return []  # пакетный менеджер не поддерживается — судим по vulkaninfo ниже
    version = packages.query(ctx, names)[names[0]]
    if version is None:
        return result(GROUP, "loader", Status.FAIL, value=t("common.not_installed"),
                      hint=t("vulkan.loader.missing_hint"), **packages.fix_for(ctx, names))
    return result(GROUP, "loader", Status.OK, value=packages.strip_version(version))


@check("icd")
def check_icd(ctx: Context):
    files = _icd_files()
    # Ждём ICD только для карт с правильным драйвером: при nouveau/radeon пакет Vulkan не поможет,
    # там проблема в самом драйвере, и о ней говорит группа «Видеокарта».
    vendors = sorted({g.vendor for g in ctx.gpus
                      if g.vendor in ICD_BY_VENDOR and g.driver in GOOD_DRIVERS[g.vendor]})
    missing = [v for v in vendors if not any(f.startswith(ICD_BY_VENDOR[v][0]) for f in files)]
    value = ", ".join(files) or t("vulkan.icd.none")
    if missing:
        resolved = [packages.component(ctx, ICD_BY_VENDOR[v][1]) for v in missing]
        pkgs = list(dict.fromkeys(p for names in resolved if names for p in names))
        hint = t("vulkan.icd.missing_hint", vendors=", ".join(VENDOR_NAMES[v] for v in missing))
        if pkgs:
            hint += " " + t("vulkan.icd.packages", packages=", ".join(pkgs))
        return result(GROUP, "icd", Status.FAIL, value=value, hint=hint,
                      **packages.fix_for(ctx, pkgs))
    if not files:
        return result(GROUP, "icd", Status.UNKNOWN, value=value)
    return result(GROUP, "icd", Status.OK, value=value)


def parse_vulkaninfo_summary(text: str) -> list[dict[str, str]]:
    """Блоки GPU0:, GPU1: … из `vulkaninfo --summary` -> список словарей ключ=значение."""
    devices: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_devices = False
    for line in text.splitlines():
        if line.startswith("Devices:"):
            in_devices = True
            continue
        if not in_devices:
            continue
        if re.match(r"^GPU\d+:", line):
            current = {}
            devices.append(current)
        elif current is not None and "=" in line:
            key, _, val = line.partition("=")
            current[key.strip()] = val.strip()
    return devices


@check("devices")
def check_devices(ctx: Context):
    if not which("vulkaninfo"):
        return result(GROUP, "devices", Status.UNKNOWN, value=t("vulkan.devices.no_tool"),
                      hint=t("vulkan.devices.no_tool_hint"),
                      **packages.fix_for(ctx, packages.component(ctx, "vulkan_tools") or []))
    out = run(["vulkaninfo", "--summary"])
    devices = parse_vulkaninfo_summary(out.stdout)
    if out.returncode != 0 or not devices:
        err = (out.stderr.strip() or out.stdout.strip()).splitlines()[-5:]
        return result(GROUP, "devices", Status.FAIL, value=t("vulkan.devices.failed"),
                      hint=t("vulkan.devices.failed_hint"), error="\n".join(err) or None)

    real = [d for d in devices if d.get("deviceType") != "PHYSICAL_DEVICE_TYPE_CPU"]
    names = "; ".join(f"{d.get('deviceName', '?')} ({d.get('driverName', '?')})" for d in devices)
    if not real:
        return result(GROUP, "devices", Status.FAIL, value=names,
                      hint=t("vulkan.devices.cpu_only_hint"))

    # Видеокарты, которые есть в системе, но которых не видит Vulkan.
    seen = {d.get("vendorID", "").lower() for d in real}
    unseen = [g.name for g in ctx.gpus if g.vendor != "unknown" and g.vendor_id.lower() not in seen]
    if unseen:
        return result(GROUP, "devices", Status.WARN, value=names,
                      hint=t("vulkan.devices.unseen_hint", gpus="; ".join(unseen)))
    return result(GROUP, "devices", Status.OK, value=names)


CHECKS = [check_loader, check_icd, check_devices]
