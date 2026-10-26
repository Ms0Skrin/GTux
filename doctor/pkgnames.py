"""Имена пакетов для разных дистрибутивов.

Проверки спрашивают «компонент» (например, 32-битный загрузчик Vulkan), а здесь он превращается
в конкретные пакеты. None или отсутствие семейства значит: для этого дистрибутива не знаем точно
и поэтому не проверяем (лучше честно промолчать, чем посоветовать несуществующий пакет).

Источники:
  Arch:   pacman -Si (сверено на живой системе), wiki.archlinux.org
  Debian: wiki.debian.org/Steam, wiki.debian.org/NvidiaGraphicsDrivers
  Ubuntu: пакеты libnvidia-gl-<ветка> в restricted
  Fedora: rpmfusion.org/Howto/NVIDIA, документация по Steam из RPM Fusion
"""

from __future__ import annotations

# семейство -> имена пакетов; строка может содержать {nvidia_branch} (например 550)
COMPONENTS: dict[str, dict[str, list[str]]] = {
    "mesa": {
        "arch": ["mesa"], "debian": ["libgl1-mesa-dri"], "ubuntu": ["libgl1-mesa-dri"],
        "fedora": ["mesa-dri-drivers"],
    },
    "nvidia_userspace": {"arch": ["nvidia-utils"]},
    "vulkan_loader": {
        "arch": ["vulkan-icd-loader"], "debian": ["libvulkan1"], "ubuntu": ["libvulkan1"],
        "fedora": ["vulkan-loader"],
    },
    "vulkan_tools": {
        "arch": ["vulkan-tools"], "debian": ["vulkan-tools"], "ubuntu": ["vulkan-tools"],
        "fedora": ["vulkan-tools"],
    },
    "vulkan_amd": {
        "arch": ["vulkan-radeon"], "debian": ["mesa-vulkan-drivers"],
        "ubuntu": ["mesa-vulkan-drivers"], "fedora": ["mesa-vulkan-drivers"],
    },
    "vulkan_intel": {
        "arch": ["vulkan-intel"], "debian": ["mesa-vulkan-drivers"],
        "ubuntu": ["mesa-vulkan-drivers"], "fedora": ["mesa-vulkan-drivers"],
    },
    "vulkan_nvidia": {"arch": ["nvidia-utils"]},
    # --- 32 бита ---
    "lib32_vulkan_loader": {
        "arch": ["lib32-vulkan-icd-loader"], "debian": ["libvulkan1:i386"],
        "ubuntu": ["libvulkan1:i386"], "fedora": ["vulkan-loader.i686"],
    },
    "lib32_amd": {
        "arch": ["lib32-mesa", "lib32-vulkan-radeon"],
        "debian": ["libgl1-mesa-dri:i386", "libglx-mesa0:i386", "mesa-vulkan-drivers:i386"],
        "ubuntu": ["libgl1-mesa-dri:i386", "libglx-mesa0:i386", "mesa-vulkan-drivers:i386"],
        "fedora": ["mesa-dri-drivers.i686", "mesa-vulkan-drivers.i686"],
    },
    "lib32_intel": {
        "arch": ["lib32-mesa", "lib32-vulkan-intel"],
        "debian": ["libgl1-mesa-dri:i386", "libglx-mesa0:i386", "mesa-vulkan-drivers:i386"],
        "ubuntu": ["libgl1-mesa-dri:i386", "libglx-mesa0:i386", "mesa-vulkan-drivers:i386"],
        "fedora": ["mesa-dri-drivers.i686", "mesa-vulkan-drivers.i686"],
    },
    "lib32_nvidia": {
        "arch": ["lib32-nvidia-utils"], "debian": ["nvidia-driver-libs:i386"],
        "ubuntu": ["libnvidia-gl-{nvidia_branch}:i386"],
        "fedora": ["xorg-x11-drv-nvidia-libs.i686"],
    },
    # --- программы ---
    "steam": {"arch": ["steam"], "debian": ["steam-installer"], "ubuntu": ["steam-installer"],
              "fedora": ["steam"]},
    "gamemode": {f: ["gamemode"] for f in ("arch", "debian", "ubuntu", "fedora")},
    "mangohud": {f: ["mangohud"] for f in ("arch", "debian", "ubuntu", "fedora")},
    "gamescope": {f: ["gamescope"] for f in ("arch", "debian", "ubuntu", "fedora")},
    "pipewire_pulse": {"arch": ["pipewire-pulse"], "debian": ["pipewire-pulse"],
                       "ubuntu": ["pipewire-pulse"], "fedora": ["pipewire-pulseaudio"]},
    # правила udev для геймпадов (сверено: packages.debian.org, mdapi.fedoraproject.org)
    "steam_devices": {f: ["steam-devices"] for f in ("arch", "debian", "ubuntu", "fedora")},
    # 32-битные части утилит уверенно знаем только для Arch
    "lib32_gamemode": {"arch": ["lib32-gamemode"]},
    "lib32_mangohud": {"arch": ["lib32-mangohud"]},
}


def resolve(component: str, family: str | None, **params) -> list[str] | None:
    """Пакеты компонента для семейства дистрибутива; None — не знаем."""
    if family is None:
        return None
    names = COMPONENTS.get(component, {}).get(family)
    if names is None:
        return None
    try:
        return [n.format(**params) for n in names]
    except KeyError:
        return None  # нужен параметр (например, ветка NVIDIA), а его нет
