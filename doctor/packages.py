"""Работа с пакетным менеджером: pacman, apt (dpkg), dnf (rpm).

Здесь только чтение («установлен ли пакет») и сборка команды установки.
Сама установка выполняется в doctor/fixer.py и только после подтверждения пользователя.
"""

from __future__ import annotations

import re
import shlex

from doctor import pkgnames
from doctor.system import run, which


class PackageManager:
    name = ""
    family = ""  # ключ в doctor.pkgnames: arch | debian | ubuntu | fedora

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


class Pacman(PackageManager):
    name = "pacman"
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

    def is_32bit(self, package):
        return package.startswith("lib32-")


class Apt(PackageManager):
    name = "apt"

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
        return package.endswith(":i386")

    def i386_enabled(self) -> bool:
        return "i386" in run(["dpkg", "--print-foreign-architectures"]).stdout.split()


class Dnf(PackageManager):
    name = "dnf"
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
    """Пакеты компонента для текущей системы (см. doctor.pkgnames)."""
    pm = ctx.package_manager
    return pkgnames.resolve(name, pm.family if pm else None, **ctx.pkg_params)


def fix_for(ctx, pkgs: list[str]) -> dict:
    """Поля для result(): команда для показа + список пакетов для автоустановки."""
    if not pkgs or ctx.package_manager is None:
        return {}
    return {"fix": ctx.package_manager.install_command(pkgs), "packages": list(pkgs)}
