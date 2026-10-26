"""Общий формат результатов проверок.

Проверки ничего не печатают сами — они возвращают CheckResult.
Дальше результат одинаково отрисовывается в терминале, в JSON, а потом — в GTK-окне и боте.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    OK = "ok"            # всё хорошо
    WARN = "warn"        # можно улучшить
    FAIL = "fail"        # проблема
    UNKNOWN = "unknown"  # не удалось проверить


@dataclass
class CheckResult:
    id: str                    # стабильный машинный id, например "gpu.driver"
    group: str                 # id группы, например "gpu"
    title: str                 # что проверяли (уже переведено)
    status: Status
    value: str = ""            # что нашли, коротко
    hint: str = ""             # пояснение: что это и чем грозит
    fix: str | None = None     # команда-исправление (только показываем, не выполняем)
    error: str | None = None   # текст ошибки, если проверка не удалась

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "group": self.group,
            "title": self.title,
            "status": self.status.value,
            "value": self.value,
            "hint": self.hint,
            "fix": self.fix,
            "error": self.error,
        }


@dataclass
class GPU:
    vendor: str        # "nvidia" | "amd" | "intel" | "unknown"
    vendor_id: str     # PCI vendor id, например 0x10de
    name: str         # человеческое название из lspci
    driver: str | None # загруженный драйвер ядра: nvidia, nouveau, amdgpu, radeon, i915, xe
    pci_slot: str      # например 0000:03:00.0


@dataclass
class Context:
    """Факты, которые одни группы находят, а другие используют."""

    distro_id: str = ""
    distro_like: list[str] = field(default_factory=list)
    package_manager: Any = None  # doctor.packages.PackageManager | None
    gpus: list[GPU] = field(default_factory=list)
    multilib_enabled: bool | None = None  # None = не проверяли
    steam_roots: list[tuple[str, Path]] = field(default_factory=list)  # [(способ установки, путь)]
    steam_libraries: list[Path] = field(default_factory=list)
