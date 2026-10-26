"""Группа 6: диски с играми. NTFS/exFAT, «грязные» тома, read-only, noexec, свободное место."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from gtux.i18n import t
from gtux.models import Context, Status
from gtux.runner import check, result
from gtux.system import CommandError, read_text, run, which

GROUP = "disks"

NTFS_TYPES = {"ntfs", "ntfs3"}
FAT_TYPES = {"vfat", "exfat", "msdos"}
LOW_SPACE_BYTES = 20 * 1024**3  # меньше 20 ГБ — обновления и кэш шейдеров могут не влезть
SEVERITY = [Status.OK, Status.UNKNOWN, Status.WARN, Status.FAIL]


@dataclass
class Mount:
    source: str
    target: str
    fstype: str
    options: set[str]


def _unescape(s: str) -> str:
    """В /proc/mounts пробел записан как \\040 и т.п."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), s)


def parse_mounts(text: str) -> list[Mount]:
    mounts = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            mounts.append(Mount(_unescape(parts[0]), _unescape(parts[1]), parts[2],
                                set(parts[3].split(","))))
    return mounts


def find_mount(path: Path, mounts: list[Mount]) -> Mount | None:
    """Точка монтирования, на которой лежит path (самая длинная подходящая)."""
    best = None
    for m in mounts:
        if path == Path(m.target) or Path(m.target) in path.parents:
            if best is None or len(m.target) >= len(best.target):
                best = m
    return best


def real_fstype(mount: Mount) -> str:
    """ntfs-3g и exfat-fuse видны как fuseblk — уточняем через lsblk."""
    if mount.fstype == "fuseblk" and mount.source.startswith("/dev/") and which("lsblk"):
        try:
            fs = run(["lsblk", "-no", "FSTYPE", mount.source]).stdout.strip()
            if fs:
                return fs
        except CommandError:
            pass
    return mount.fstype


def is_rotational(source: str) -> bool | None:
    """True — жёсткий диск (HDD), False — SSD/NVMe, None — не понять (LVM, LUKS, сеть…)."""
    if not source.startswith("/dev/"):
        return None
    block = Path("/sys/class/block") / Path(source).resolve().name
    if not block.exists():
        return None
    disk = block.resolve()
    if (disk / "partition").exists():
        disk = disk.parent  # раздел -> весь диск
    value = read_text(disk / "queue" / "rotational")
    return value == "1" if value in ("0", "1") else None


def kernel_dirty_messages() -> list[str] | None:
    """Строки журнала ядра о «грязных» NTFS-томах. None — журнал прочитать не удалось."""
    if not which("journalctl"):
        return None
    try:
        out = run(["journalctl", "-k", "-b", "--no-pager", "-o", "cat"])
    except CommandError:
        return None
    if out.returncode != 0:
        return None
    pattern = re.compile(r"ntfs.*(dirty|unclean|hibernat)", re.IGNORECASE)
    return [line for line in out.stdout.splitlines() if pattern.search(line)]


def human_size(n: int) -> str:
    return t("common.gb", n=f"{n / 1024**3:.0f}")


def _compatdata_path(lib: Path) -> Path:
    return lib / "steamapps" / "compatdata"


def assess_library(lib: Path, mounts: list[Mount], dirty_log: list[str] | None) -> dict:
    mount = find_mount(lib.resolve(), mounts)
    if mount is None:
        return {"status": Status.UNKNOWN, "value": str(lib), "error": t("disks.no_mount")}
    fstype = real_fstype(mount)
    findings: list[tuple[Status, str]] = []

    # --- файловая система ---
    compat = _compatdata_path(lib)
    compat_mount = find_mount(compat.resolve(), mounts) if compat.exists() else mount
    compat_fs = real_fstype(compat_mount) if compat_mount else fstype
    compat_moved = compat_mount is not None and compat_mount.target != mount.target \
        and compat_fs not in NTFS_TYPES | FAT_TYPES
    if fstype in NTFS_TYPES:
        if compat_moved:
            findings.append((Status.WARN, t("disks.ntfs_compat_moved_hint", target=compat.resolve())))
        elif "windows_names" in mount.options:
            findings.append((Status.FAIL, t("disks.ntfs_windows_names_hint")))
        else:
            findings.append((Status.WARN, t("disks.ntfs_hint")))
    elif fstype in FAT_TYPES:
        if compat_moved:
            findings.append((Status.WARN, t("disks.fat_compat_moved_hint", fs=fstype)))
        else:
            findings.append((Status.FAIL, t("disks.fat_hint", fs=fstype)))

    # --- опции монтирования ---
    if "ro" in mount.options:
        findings.append((Status.FAIL, t("disks.ro_hint")))
    elif not os.access(lib, os.W_OK):
        findings.append((Status.FAIL, t("disks.not_writable_hint")))
    if "noexec" in mount.options:
        findings.append((Status.FAIL, t("disks.noexec_hint")))

    # --- «грязный» том ---
    if fstype in NTFS_TYPES:
        dev = Path(mount.source).name
        if dirty_log is None:
            findings.append((Status.UNKNOWN, t("disks.dirty_unknown")))
        elif any(dev in line for line in dirty_log):
            findings.append((Status.FAIL, t("disks.dirty_hint")))

    # --- жёсткий диск ---
    if is_rotational(mount.source):
        findings.append((Status.WARN, t("disks.hdd_hint")))

    # --- свободное место ---
    try:
        free = shutil.disk_usage(lib).free
    except OSError:
        free = None
    if free is not None and free < LOW_SPACE_BYTES:
        findings.append((Status.WARN, t("disks.low_space_hint", free=human_size(free))))

    value = t("disks.value", fs=fstype, source=mount.source,
              free=human_size(free) if free is not None else "?")
    if fstype in NTFS_TYPES | FAT_TYPES:
        value += "\n" + t("disks.compat_line", path=compat.resolve(), fs=compat_fs)
    status = max((s for s, _ in findings), key=SEVERITY.index, default=Status.OK)
    hint = "\n".join(h for _, h in findings)
    return {"status": status, "value": value, "hint": hint}


@check("library")
def check_libraries(ctx: Context):
    if not ctx.steam_libraries:
        return result(GROUP, "library", Status.UNKNOWN, value=t("disks.no_libraries"))
    text = read_text("/proc/self/mounts")
    if text is None:
        return result(GROUP, "library", Status.UNKNOWN, error=t("disks.no_proc_mounts"))
    mounts = parse_mounts(text)
    present = [lib for lib in ctx.steam_libraries if lib.exists()]
    if not present:
        return []  # о пропавших библиотеках уже сказала группа Steam
    needs_log = any((m := find_mount(lib.resolve(), mounts)) and real_fstype(m) in NTFS_TYPES
                    for lib in present)
    dirty_log = kernel_dirty_messages() if needs_log else []
    results = []
    for i, lib in enumerate(present):
        verdict = assess_library(lib, mounts, dirty_log)
        results.append(result(GROUP, f"library.{i}", title=t("disks.library.title", path=lib),
                              **verdict))
    return results


CHECKS = [check_libraries]
