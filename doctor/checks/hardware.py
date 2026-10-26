"""Группа: железо и устройства — память и swap, звук, геймпады."""

from __future__ import annotations

from pathlib import Path

from doctor import packages
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result
from doctor.system import read_text

GROUP = "hardware"

LOW_RAM_GIB = 8
UDEV_DIRS = [Path("/usr/lib/udev/rules.d"), Path("/lib/udev/rules.d"), Path("/etc/udev/rules.d")]
VALVE_USB_VENDOR = "28de"  # Steam Controller, Steam Deck, Index — по нему узнаём правила steam-devices


def parse_meminfo(text: str) -> dict[str, int]:
    """{поле: байты} из /proc/meminfo (там килобайты)."""
    out = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            out[key] = int(parts[0]) * 1024
    return out


def running_processes() -> set[str]:
    """Имена запущенных процессов из /proc/*/comm (без сторонних утилит)."""
    names = set()
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            names.add(comm.read_text().strip())
        except OSError:
            continue  # процесс успел завершиться
    return names


def _gib(n: int) -> str:
    return t("common.gb", n=f"{n / 1024**3:.0f}")


@check("memory")
def check_memory(ctx: Context):
    text = read_text("/proc/meminfo")
    if text is None:
        return result(GROUP, "memory", Status.UNKNOWN, error=t("hardware.memory.unreadable"))
    mem = parse_meminfo(text)
    ram, swap = mem.get("MemTotal", 0), mem.get("SwapTotal", 0)
    swaps = read_text("/proc/swaps") or ""
    kind = " (zram)" if "zram" in swaps else ""
    value = t("hardware.memory.value", ram=_gib(ram), swap=_gib(swap) + kind if swap else t("hardware.memory.no_swap"))
    findings = []
    # MemTotal меньше физического объёма (часть занимает ядро), поэтому порог с запасом
    if ram and ram < (LOW_RAM_GIB - 0.75) * 1024**3:
        findings.append(t("hardware.memory.low_ram_hint", gb=LOW_RAM_GIB))
    if swap == 0:
        findings.append(t("hardware.memory.no_swap_hint"))
    if findings:
        return result(GROUP, "memory", Status.WARN, value=value, hint="\n".join(findings))
    return result(GROUP, "memory", Status.OK, value=value)


@check("audio")
def check_audio(ctx: Context):
    procs = running_processes()
    if "pipewire" in procs:
        if "pipewire-pulse" not in procs and "pulseaudio" not in procs:
            names = packages.component(ctx, "pipewire_pulse") or []
            return result(GROUP, "audio", Status.FAIL, value="PipeWire",
                          hint=t("hardware.audio.no_pulse_hint"), **packages.fix_for(ctx, names))
        return result(GROUP, "audio", Status.OK, value="PipeWire + pipewire-pulse")
    if "pulseaudio" in procs:
        return result(GROUP, "audio", Status.OK, value="PulseAudio")
    return result(GROUP, "audio", Status.WARN, value=t("hardware.audio.none"),
                  hint=t("hardware.audio.none_hint"))


@check("controllers")
def check_controllers(ctx: Context):
    found = []
    for d in UDEV_DIRS:
        if not d.is_dir():
            continue
        for rules in sorted(d.glob("*.rules")):
            try:
                if VALVE_USB_VENDOR in rules.read_text(errors="replace"):
                    found.append(rules.name)
            except OSError:
                continue
    if not found:
        names = packages.component(ctx, "steam_devices") or []
        return result(GROUP, "controllers", Status.WARN, value=t("hardware.controllers.none"),
                      hint=t("hardware.controllers.none_hint"), **packages.fix_for(ctx, names))
    return result(GROUP, "controllers", Status.OK, value=", ".join(dict.fromkeys(found)))


CHECKS = [check_memory, check_audio, check_controllers]
