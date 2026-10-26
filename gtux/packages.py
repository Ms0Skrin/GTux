"""Работа с пакетным менеджером: pacman, apt (dpkg), dnf (rpm).

Здесь только чтение («установлен ли пакет») и сборка команды установки.
Сама установка выполняется в gtux/fixer.py и только после подтверждения пользователя.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from gtux import pkgnames
from gtux.system import run, which


APT_LISTS = "/var/lib/apt/lists"  # сюда apt update кладёт списки пакетов


class PackageManager:
    name = ""
    assume_yes = ""  # флаг «не спрашивать»: в окне подтверждение уже получено
    family = ""  # ключ в gtux.pkgnames: arch | debian | ubuntu | fedora

    def installed_versions(self, packages: list[str]) -> dict[str, str | None]:
        """{пакет: версия или None, если не установлен}."""
        raise NotImplementedError

    def install_argv(self, packages: list[str]) -> list[str]:
        raise NotImplementedError

    def install_command(self, packages: list[str]) -> str:
        """Команда установки строкой — для показа пользователю."""
        return shlex.join(self.install_argv(packages))

    def is_32bit(self, package: str) -> bool:
        """Нужна ли для пакета включённая 32-битная архитектура (multilib / i386)."""
        raise NotImplementedError

    def unavailable(self, packages: list[str]) -> list[str] | None:
        """Пакеты, которых нет в подключённых репозиториях; None — узнать не удалось (не мешаем установке).
        Читает только локальные списки пакетов, в интернет не ходит."""
        return None


class Pacman(PackageManager):
    name = "pacman"
    assume_yes = "--noconfirm"
    family = "arch"

    def installed_versions(self, packages):
        result: dict[str, str | None] = {p: None for p in packages}
        if not packages:
            return result
        # pacman -Q печатает «имя версия» для найденных и ошибку для остальных.
        out = run(["pacman", "-Q", *packages])
        for line in out.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in result:
                result[parts[0]] = parts[1]
        return result

    def install_argv(self, packages):
        return ["sudo", "pacman", "-S", "--needed", *packages]

    def unavailable(self, packages):
        if not packages:
            return []
        # «error: package 'x' was not found» — для каждого пакета, которого нет в базах pacman
        out = run(["pacman", "-Si", *packages])
        missing = set(re.findall(r"package '([^']+)' was not found", out.stderr))
        return [p for p in packages if p in missing]

    # В Arch эти пакеты лежат в репозитории multilib, хоть и без префикса lib32- (pacman -Si, 2026-10)
    MULTILIB = {"steam", "steam-devices"}

    def is_32bit(self, package):
        return package.startswith("lib32-") or package in self.MULTILIB


class Apt(PackageManager):
    name = "apt"
    assume_yes = "-y"

    def __init__(self, ubuntu: bool = False):
        self.family = "ubuntu" if ubuntu else "debian"
        self._native_arch: str | None = None

    def native_arch(self) -> str:
        if self._native_arch is None:
            self._native_arch = run(["dpkg", "--print-architecture"]).stdout.strip() or "amd64"
        return self._native_arch

    def installed_versions(self, packages):
        result: dict[str, str | None] = {}
        for pkg in packages:
            # Без явной архитектуры dpkg-query может вернуть сразу amd64 и i386 — уточняем.
            query = pkg if ":" in pkg else f"{pkg}:{self.native_arch()}"
            out = run(["dpkg-query", "-W", "-f=${db:Status-Abbrev} ${Version}\n", query])
            line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
            status, _, version = line.partition(" ")
            # «ii» — установлен; «hi» — установлен и зафиксирован (hold)
            result[pkg] = version.strip() if out.returncode == 0 and status[:2] in ("ii", "hi") else None
        return result

    def install_argv(self, packages):
        return ["sudo", "apt", "install", *packages]

    def is_32bit(self, package):
        # steam-installer ставит 32-битные библиотеки: без i386 apt его не поставит (wiki.debian.org/Steam)
        return package.endswith(":i386") or package == "steam-installer"

    def unavailable(self, packages):
        # i386-пакеты проверяем по 64-битному имени: пока i386 не включён, apt их не видит,
        # а раздел (main/contrib/non-free, universe/multiverse) у них общий
        base = {p: p.removesuffix(":i386") for p in packages}
        names = sorted(set(base.values()))
        if not names:
            return []
        out = run(["apt-cache", "policy", *names])
        candidate: dict[str, str] = {}
        current = None
        for line in out.stdout.splitlines():
            if line and not line[0].isspace() and line.endswith(":"):
                current = line[:-1]
            elif current and line.strip().startswith("Candidate:"):
                candidate[current] = line.split(":", 1)[1].strip()
        if not any(Path(APT_LISTS).glob("*_Packages*")):
            return None  # списки пакетов не скачаны (apt update не делали) — судить нельзя
        ok = {n for n, c in candidate.items() if c and c != "(none)"}
        return [p for p in packages if base[p] not in ok]

    def i386_enabled(self) -> bool:
        return "i386" in run(["dpkg", "--print-foreign-architectures"]).stdout.split()


class Dnf(PackageManager):
    name = "dnf"
    assume_yes = "-y"
    family = "fedora"

    def installed_versions(self, packages):
        result: dict[str, str | None] = {}
        for pkg in packages:
            out = run(["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}\n", pkg])
            lines = out.stdout.strip().splitlines()
            result[pkg] = lines[0] if out.returncode == 0 and lines else None
        return result

    def install_argv(self, packages):
        return ["sudo", "dnf", "install", *packages]

    def unavailable(self, packages):
        base = {p: p.removesuffix(".i686") for p in packages}
        names = sorted(set(base.values()))
        if not names:
            return []
        # -C: только кэш, без скачивания метаданных; пустой ответ — кэша нет, судить нельзя
        out = run(["dnf", "-C", "-q", "repoquery", "--qf", "%{name}\n", *names], timeout=60)
        found = set(out.stdout.split())
        if not found:
            return None
        return [p for p in packages if base[p] not in found]

    def is_32bit(self, package):
        return package.endswith(".i686")


def detect(distro_ids: list[str] | None = None) -> PackageManager | None:
    """distro_ids — ID и ID_LIKE из os-release, чтобы отличить Ubuntu от Debian."""
    ids = distro_ids or []
    if which("pacman"):
        return Pacman()
    if which("dpkg-query") and which("apt-get"):
        return Apt(ubuntu=any(i in ("ubuntu", "linuxmint", "pop") for i in ids))
    if which("rpm") and which("dnf"):
        return Dnf()
    return None


def strip_version(version: str) -> str:
    """'3:26.2.4-1' -> '26.2.4' (убираем epoch и номер сборки пакета)."""
    version = version.split(":", 1)[-1]
    return re.sub(r"-[^-]+$", "", version)


def query(ctx, packages: list[str]) -> dict[str, str | None] | None:
    """None, если пакетный менеджер не поддерживается. Ошибки не прячем — они всплывут в проверку."""
    pm = ctx.package_manager
    if pm is None:
        return None
    return pm.installed_versions(packages)


def component(ctx, name: str) -> list[str] | None:
    """Пакеты компонента для текущей системы (см. gtux.pkgnames)."""
    pm = ctx.package_manager
    return pkgnames.resolve(name, pm.family if pm else None, **ctx.pkg_params)


def fix_for(ctx, pkgs: list[str]) -> dict:
    """Поля для result(): команда для показа + список пакетов для автоустановки."""
    if not pkgs or ctx.package_manager is None:
        return {}
    return {"fix": ctx.package_manager.install_command(pkgs), "packages": list(pkgs)}
