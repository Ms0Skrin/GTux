"""Работа с пакетным менеджером.

Сейчас только чтение («установлен ли пакет») и только pacman.
Позже сюда добавятся apt/dnf и установка недостающего одной кнопкой.
"""

from __future__ import annotations

import re

from doctor.system import run, which


class PackageManager:
    name = ""

    def installed_versions(self, packages: list[str]) -> dict[str, str | None]:
        """{пакет: версия или None, если не установлен}."""
        raise NotImplementedError

    def install_command(self, packages: list[str]) -> str:
        """Команда установки — только для показа пользователю."""
        raise NotImplementedError


class Pacman(PackageManager):
    name = "pacman"

    def installed_versions(self, packages: list[str]) -> dict[str, str | None]:
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

    def install_command(self, packages: list[str]) -> str:
        return "sudo pacman -S --needed " + " ".join(packages)


def detect() -> PackageManager | None:
    if which("pacman"):
        return Pacman()
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
