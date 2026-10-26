"""Группа 2: видеокарта, драйвер и его версия."""

from __future__ import annotations

import re
from pathlib import Path

from doctor import packages
from doctor.i18n import t
from doctor.models import GPU, Context, Status
from doctor.runner import check, result
from doctor.system import CommandError, read_text, run, which

GROUP = "gpu"

VENDORS = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}
VENDOR_NAMES = {"nvidia": "NVIDIA", "amd": "AMD", "intel": "Intel", "unknown": "?"}

# Какой драйвер ядра для какого вендора считаем «игровым».
GOOD_DRIVERS = {"nvidia": {"nvidia"}, "amd": {"amdgpu"}, "intel": {"i915", "xe"}}

WIKI = {
    "nvidia": "https://wiki.archlinux.org/title/NVIDIA",
    "amd": "https://wiki.archlinux.org/title/AMDGPU",
    "intel": "https://wiki.archlinux.org/title/Intel_graphics",
}


def detect_gpus() -> list[GPU]:
    """Видеокарты из /sys/class/drm — работает без lspci и без прав root."""
    gpus: dict[str, GPU] = {}
    for card in sorted(Path("/sys/class/drm").glob("card*")):
        if not re.fullmatch(r"card\d+", card.name):
            continue  # card1-DP-1 и т.п. — это разъёмы, а не карты
        device = (card / "device").resolve()
        vendor_id = read_text(device / "vendor")
        if vendor_id is None:
            continue  # не PCI-устройство (например, simpledrm)
        slot = device.name
        driver_link = device / "driver"
        driver = driver_link.resolve().name if driver_link.exists() else None
        vendor = VENDORS.get(vendor_id, "unknown")
        gpus[slot] = GPU(vendor=vendor, vendor_id=vendor_id, name=_pci_name(slot, vendor),
                         driver=driver, pci_slot=slot)
    return list(gpus.values())


def _pci_name(slot: str, vendor: str) -> str:
    if which("lspci"):
        try:
            out = run(["lspci", "-s", slot]).stdout.strip()
            # "03:00.0 VGA compatible controller: NVIDIA Corporation GA104 [GeForce RTX 3060 Ti] (rev a1)"
            if ": " in out:
                return re.sub(r"\s*\(rev \w+\)$", "", out.split(": ", 1)[1])
        except CommandError:
            pass  # название — не критично, ниже есть запасной вариант
    return f"{VENDOR_NAMES[vendor]} ({slot})"


@check("detect")
def check_detect(ctx: Context):
    ctx.gpus = detect_gpus()
    if not ctx.gpus:
        return result(GROUP, "detect", Status.UNKNOWN, value=t("gpu.detect.none"),
                      error=t("gpu.detect.none_error"))
    return result(GROUP, "detect", Status.OK, value="; ".join(g.name for g in ctx.gpus))


@check("driver")
def check_driver(ctx: Context):
    if not ctx.gpus:
        return result(GROUP, "driver", Status.UNKNOWN, value=t("gpu.no_gpus"))
    results = []
    for i, gpu in enumerate(ctx.gpus):
        title = t("gpu.driver.title_for", name=gpu.name) if len(ctx.gpus) > 1 else t("gpu.driver.title")
        cid = f"driver.{i}" if len(ctx.gpus) > 1 else "driver"
        results.append(result(GROUP, cid, title=title, **_driver_verdict(gpu)))
    return results


def _driver_verdict(gpu: GPU) -> dict:
    drv = gpu.driver
    if gpu.vendor == "unknown":
        return {"status": Status.UNKNOWN, "value": drv or "—",
                "hint": t("gpu.driver.unknown_vendor", vendor_id=gpu.vendor_id)}
    if drv is None:
        return {"status": Status.FAIL, "value": t("gpu.driver.not_loaded"),
                "hint": t("gpu.driver.not_loaded_hint", wiki=WIKI[gpu.vendor])}
    if drv in GOOD_DRIVERS[gpu.vendor]:
        return {"status": Status.OK, "value": drv}
    if gpu.vendor == "nvidia" and drv == "nouveau":
        return {"status": Status.WARN, "value": drv,
                "hint": t("gpu.driver.nouveau_hint", wiki=WIKI["nvidia"])}
    if gpu.vendor == "amd" and drv == "radeon":
        return {"status": Status.FAIL, "value": drv,
                "hint": t("gpu.driver.radeon_hint", wiki=WIKI["amd"])}
    return {"status": Status.WARN, "value": drv,
            "hint": t("gpu.driver.unexpected_hint", wiki=WIKI[gpu.vendor])}


@check("nvidia_version")
def check_nvidia_version(ctx: Context):
    if not any(g.vendor == "nvidia" and g.driver == "nvidia" for g in ctx.gpus):
        return []  # не наш случай — строку не показываем
    loaded = read_text("/sys/module/nvidia/version")
    if loaded is None:
        return result(GROUP, "nvidia_version", Status.UNKNOWN,
                      error=t("gpu.nvidia_version.no_sysfs"))
    pkgs = packages.query(ctx, ["nvidia-utils"])
    userspace = pkgs.get("nvidia-utils") if pkgs else None
    if userspace and packages.strip_version(userspace) != loaded:
        # Классика после обновления без перезагрузки: «Driver/library version mismatch».
        return result(GROUP, "nvidia_version", Status.FAIL,
                      value=t("gpu.nvidia_version.mismatch", loaded=loaded,
                              userspace=packages.strip_version(userspace)),
                      hint=t("gpu.nvidia_version.mismatch_hint"), fix="reboot")
    return result(GROUP, "nvidia_version", Status.OK, value=loaded)


@check("mesa_version")
def check_mesa_version(ctx: Context):
    if not any(g.vendor in ("amd", "intel") for g in ctx.gpus):
        return []  # Mesa для NVIDIA-драйвера не главная, не путаем пользователя
    pkgs = packages.query(ctx, ["mesa"])
    if pkgs and pkgs.get("mesa"):
        return result(GROUP, "mesa_version", Status.OK, value=packages.strip_version(pkgs["mesa"]))
    if which("glxinfo"):
        out = run(["glxinfo", "-B"]).stdout
        m = re.search(r"Mesa (\d+\.\d+\.\d+\S*)", out)
        if m:
            return result(GROUP, "mesa_version", Status.OK, value=m[1])
    return result(GROUP, "mesa_version", Status.UNKNOWN, error=t("gpu.mesa_version.not_found"))


CHECKS = [check_detect, check_driver, check_nvidia_version, check_mesa_version]
