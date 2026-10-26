"""Группа 9: системные настройки — governor процессора, vm.max_map_count, лимит открытых файлов."""

from __future__ import annotations

import resource
from collections import Counter
from pathlib import Path

from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result
from doctor.system import read_text

GROUP = "tuning"

# Значение по умолчанию в SteamOS и в Arch (пакет filesystem); старое ядерное — 65530.
MAX_MAP_COUNT_GOOD = 1048576
# Столько файлов нужно esync в Wine/Proton (жёсткий лимит; мягкий Wine поднимает сам).
NOFILE_GOOD = 524288

CPUFREQ = Path("/sys/devices/system/cpu")
# Драйверы, у которых powersave — это нормальный «умный» режим с EPP, а не минимальная частота.
EPP_DRIVERS = {"intel_pstate", "amd-pstate-epp"}


@check("governor")
def check_governor(ctx: Context):
    govs = Counter(read_text(p) for p in CPUFREQ.glob("cpu[0-9]*/cpufreq/scaling_governor"))
    govs.pop(None, None)
    if not govs:
        return result(GROUP, "governor", Status.UNKNOWN, value=t("tuning.governor.none"))
    driver = read_text(CPUFREQ / "cpu0/cpufreq/scaling_driver") or "?"
    epp = read_text(CPUFREQ / "cpu0/cpufreq/energy_performance_preference")
    value = ", ".join(f"{g} ×{n}" if len(govs) > 1 else g for g, n in govs.items())
    value += t("tuning.governor.driver", driver=driver)
    if epp:
        value += f", EPP: {epp}"

    main = govs.most_common(1)[0][0]
    if main == "powersave" and driver in EPP_DRIVERS:
        if epp == "power":
            return result(GROUP, "governor", Status.WARN, value=value, hint=t("tuning.governor.epp_power_hint"))
        return result(GROUP, "governor", Status.OK, value=value)
    if main == "powersave":
        return result(GROUP, "governor", Status.WARN, value=value, hint=t("tuning.governor.powersave_hint"))
    return result(GROUP, "governor", Status.OK, value=value)


@check("max_map_count")
def check_max_map_count(ctx: Context):
    raw = read_text("/proc/sys/vm/max_map_count")
    if raw is None or not raw.isdigit():
        return result(GROUP, "max_map_count", Status.UNKNOWN, error=t("tuning.max_map_count.unreadable"))
    if int(raw) < MAX_MAP_COUNT_GOOD:
        return result(GROUP, "max_map_count", Status.WARN, value=raw,
                      hint=t("tuning.max_map_count.low_hint", good=MAX_MAP_COUNT_GOOD),
                      fix=f"echo 'vm.max_map_count = {MAX_MAP_COUNT_GOOD}' | sudo tee "
                          "/etc/sysctl.d/80-gamecompatibility.conf && sudo sysctl --system")
    return result(GROUP, "max_map_count", Status.OK, value=raw)


@check("nofile")
def check_nofile(ctx: Context):
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    fmt = lambda n: t("tuning.nofile.unlimited") if n == resource.RLIM_INFINITY else str(n)  # noqa: E731
    value = t("tuning.nofile.value", soft=fmt(soft), hard=fmt(hard))
    if hard != resource.RLIM_INFINITY and hard < NOFILE_GOOD:
        return result(GROUP, "nofile", Status.WARN, value=value,
                      hint=t("tuning.nofile.low_hint", good=NOFILE_GOOD))
    return result(GROUP, "nofile", Status.OK, value=value)


CHECKS = [check_governor, check_max_map_count, check_nofile]
