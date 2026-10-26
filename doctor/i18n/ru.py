"""Русские тексты интерфейса. Ключи — стабильные, значения можно свободно править."""

TEXTS = {
    # --- общее ---
    "app.title": "Доктор Linux-геймера",
    "app.subtitle": "Только проверяю, ничего не меняю в системе",
    "common.not_installed": "не установлен",
    "common.crashed": "проверка упала с ошибкой",
    "status.ok": "ОК",
    "status.warn": "МОЖНО ЛУЧШЕ",
    "status.fail": "ПРОБЛЕМА",
    "status.unknown": "НЕ ПРОВЕРЕНО",
    "ui.col.status": "Статус",
    "ui.col.check": "Проверка",
    "ui.col.result": "Результат",
    "ui.fix": "Исправить: ",
    "ui.error": "Ошибка: ",
    "ui.summary": "Итого — ок: {ok}, можно улучшить: {warn}, проблем: {fail}, не проверено: {unknown}",
    "ui.all_good": "Серьёзных проблем не найдено.",
    "ui.has_problems": "Есть проблемы — см. красные строки выше.",
    "ui.note": "Команды исправления только показаны. Программа их не выполняет.",
    "cli.description": "Проверяет Linux-систему и объясняет, чего не хватает для игр.",
    "cli.json": "вывести результат в JSON (для скриптов, бота, GUI)",
    "cli.lang": "язык интерфейса",
    "cli.need_rich": (
        "Не найдена библиотека rich для красивого вывода.\n"
        "Установите её (Arch: sudo pacman -S python-rich) или запустите с --json."
    ),

    # --- группы ---
    "group.distro": "Система",
    "group.gpu": "Видеокарта",
    "group.vulkan": "Vulkan",

    # --- система ---
    "distro.os.title": "Дистрибутив",
    "distro.os.no_file": "не удалось прочитать /etc/os-release",
    "distro.os.based_on": " (основан на {base})",
    "distro.kernel.title": "Ядро",
    "distro.kernel.unparsed": "не удалось разобрать номер версии ядра",
    "distro.kernel.old_hint": (
        "Ядро старше 5.16: в нём нет futex_waitv, и Proton не сможет включить fsync. "
        "Игры будут работать, но местами медленнее. Обновите систему или поставьте более новое ядро."
    ),
    "distro.package_manager.title": "Пакетный менеджер",
    "distro.package_manager.none": "не найден",
    "distro.package_manager.aur": ", AUR: {helpers}",
    "distro.package_manager.flatpak": ", есть flatpak",
    "distro.package_manager.unsupported_hint": (
        "Пока программа умеет проверять пакеты только через pacman (Arch и производные). "
        "Проверки, которым нужен список пакетов, будут пропущены."
    ),

    # --- видеокарта ---
    "gpu.no_gpus": "видеокарты не найдены",
    "gpu.detect.title": "Видеокарта",
    "gpu.detect.none": "не найдена",
    "gpu.detect.none_error": "в /sys/class/drm нет ни одной PCI-видеокарты (виртуалка или контейнер?)",
    "gpu.driver.title": "Драйвер",
    "gpu.driver.title_for": "Драйвер: {name}",
    "gpu.driver.unknown_vendor": "Производитель видеокарты не опознан (PCI vendor {vendor_id}).",
    "gpu.driver.not_loaded": "не загружен",
    "gpu.driver.not_loaded_hint": (
        "Для видеокарты не загружен драйвер. Без него нет ускорения графики, игры не запустятся. "
        "Как поставить: {wiki}"
    ),
    "gpu.driver.nouveau_hint": (
        "Работает открытый драйвер nouveau. Для игр он обычно сильно медленнее фирменного драйвера NVIDIA. "
        "Какой пакет NVIDIA нужен, зависит от поколения карты: {wiki}"
    ),
    "gpu.driver.radeon_hint": (
        "Работает старый драйвер radeon, а у него нет Vulkan, поэтому Proton/DXVK не заработают. "
        "Карты поколений GCN 1.0/2.0 можно перевести на amdgpu параметрами ядра: {wiki}"
    ),
    "gpu.driver.unexpected_hint": "Загружен необычный драйвер. Проверьте, тот ли это драйвер, что нужен: {wiki}",
    "gpu.nvidia_version.title": "Версия драйвера NVIDIA",
    "gpu.nvidia_version.no_sysfs": "нет файла /sys/module/nvidia/version",
    "gpu.nvidia_version.mismatch": "в памяти {loaded}, в пакете {userspace}",
    "gpu.nvidia_version.mismatch_hint": (
        "Драйвер обновили, но компьютер ещё не перезагружали. Пока так, игры и Vulkan могут "
        "не запускаться с ошибкой «version mismatch». Нужно перезагрузиться."
    ),
    "gpu.mesa_version.title": "Версия Mesa",
    "gpu.mesa_version.not_found": "не удалось узнать версию Mesa: нет пакета mesa и нет glxinfo",

    # --- Vulkan ---
    "vulkan.loader.title": "Загрузчик Vulkan",
    "vulkan.loader.missing_hint": "Без загрузчика Vulkan не работает ни одна игра на Vulkan, DXVK и VKD3D (а значит, и Proton).",
    "vulkan.icd.title": "Vulkan-драйверы (ICD)",
    "vulkan.icd.none": "не найдены",
    "vulkan.icd.missing_hint": (
        "Нет Vulkan-драйвера для: {vendors}. Без него игры через Proton не запустятся "
        "или пойдут на процессоре. Нужный пакет: {packages}."
    ),
    "vulkan.devices.title": "Vulkan видит видеокарту",
    "vulkan.devices.no_tool": "нет vulkaninfo",
    "vulkan.devices.no_tool_hint": "Утилита vulkaninfo нужна только для проверки, играм она не требуется.",
    "vulkan.devices.failed": "vulkaninfo завершился с ошибкой",
    "vulkan.devices.failed_hint": "Vulkan не смог запуститься. Чаще всего причина в драйвере, текст ошибки ниже.",
    "vulkan.devices.cpu_only_hint": (
        "Vulkan видит только программный рендер на процессоре (llvmpipe). Игры будут работать "
        "очень медленно или не запустятся. Проверьте драйвер видеокарты."
    ),
    "vulkan.devices.unseen_hint": "Эти видеокарты есть в системе, но Vulkan их не видит: {gpus}.",
}
