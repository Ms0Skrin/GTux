"""Русские тексты интерфейса. Ключи — стабильные, значения можно свободно править."""

TEXTS = {
    # --- общее ---
    "app.title": "Доктор Linux-геймера",
    "app.subtitle": "Только проверяю, ничего не меняю в системе",
    "common.not_installed": "не установлен",
    "common.crashed": "проверка упала с ошибкой",
    "common.gb": "{n} ГБ",
    "common.mb": "{n} МБ",
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
    "group.multilib": "32-битная поддержка",
    "group.steam": "Steam",
    "group.disks": "Диски с играми",
    "group.proton": "Proton",
    "group.tools": "Игровые утилиты",
    "group.tuning": "Настройки системы",

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
        "Программа умеет проверять пакеты через pacman, apt и dnf. "
        "Здесь другой менеджер, проверки пакетов будут пропущены."
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
    "gpu.rebar.title": "Resizable BAR",
    "gpu.rebar.title_for": "Resizable BAR: {name}",
    "gpu.rebar.on": "включён",
    "gpu.rebar.off": "выключен",
    "gpu.rebar.value": "окно {bar}, видеопамять {vram}",
    "gpu.rebar.no_bars": "не удалось прочитать BAR видеокарты из /sys",
    "gpu.rebar.off_capable_hint": (
        "Карта умеет ReBAR, но он выключен. В UEFI включите «Above 4G Decoding» и "
        "«Re-Size BAR», CSM выключите. Даёт прирост FPS в части игр, особенно на AMD."
    ),
    "gpu.rebar.unsupported_hint": (
        "Карта или плата не объявляют поддержку ReBAR. Иногда помогает обновление BIOS "
        "или прошивки видеокарты. Не критично."
    ),
    "gpu.mesa_version.not_found": "не удалось узнать версию Mesa: нет пакета mesa и нет glxinfo",

    # --- Vulkan ---
    "vulkan.loader.title": "Загрузчик Vulkan",
    "vulkan.loader.missing_hint": "Без загрузчика Vulkan не работает ни одна игра на Vulkan, DXVK и VKD3D (а значит, и Proton).",
    "vulkan.icd.title": "Vulkan-драйверы (ICD)",
    "vulkan.icd.none": "не найдены",
    "vulkan.icd.missing_hint": (
        "Нет Vulkan-драйвера для: {vendors}. Без него игры через Proton не запустятся "
        "или пойдут на процессоре."
    ),
    "vulkan.icd.packages": "Нужный пакет: {packages}.",
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

    # --- 32 бита ---
    "multilib.unsupported": "для этого дистрибутива пока не проверяем",
    "multilib.repo.title": "32-битные пакеты (multilib / i386)",
    "multilib.repo.i386_enabled": "архитектура i386 включена",
    "multilib.repo.i386_disabled": "архитектура i386 выключена",
    "multilib.repo.i386_hint": "Без i386 не поставить 32-битные библиотеки, а без них не работают Steam и многие игры.",
    "multilib.repo.fedora": "пакеты .i686 доступны всегда",
    "multilib.repo.no_conf": "не удалось прочитать {path}",
    "multilib.repo.enabled": "включён",
    "multilib.repo.disabled": "выключен",
    "multilib.repo.disabled_hint": (
        "Без multilib нельзя поставить 32-битные библиотеки, а без них не работает Steam "
        "и многие игры. В {path} уберите # перед строками [multilib] и Include под ней, "
        "затем обновите базы пакетов."
    ),
    "multilib.packages.title": "32-битные драйверы и Vulkan",
    "multilib.packages.missing": "нет: {packages}",
    "multilib.packages.missing_hint": (
        "32-битные игры и сам Steam не увидят видеокарту: будут вылеты при запуске "
        "или ошибка «no Vulkan device»."
    ),
    "multilib.packages.enable_first": "Сначала включите 32-битные пакеты (см. строку выше).",
    "multilib.packages.unknown_vendor": "32-битный драйвер для {vendors} на этом дистрибутиве не проверяем.",
    "multilib.nvidia_match.title": "Версии драйвера NVIDIA 64/32 бит",
    "multilib.nvidia_match.differ": "64 бит: {v64}, 32 бит: {v32}",
    "multilib.nvidia_match.differ_hint": (
        "Части драйвера разных версий. 32-битные игры могут падать. "
        "Обычно лечится полным обновлением системы."
    ),

    # --- Steam ---
    "steam.install.title": "Установка Steam",
    "steam.install.package": "пакет {version}",
    "steam.install.other": "другой способ (папка есть, пакета нет)",
    "steam.install.not_found": "не найден",
    "steam.install.not_found_hint": "Steam не установлен. Если играете через Heroic или Lutris, это не проблема.",
    "steam.install.fedora_hint": "На Fedora пакет steam есть в репозитории RPM Fusion nonfree, его нужно подключить.",
    "steam.install.several_hint": "Steam стоит несколькими способами. Легко запутаться, где какие игры и настройки.",
    "steam.libraries.title": "Библиотеки игр",
    "steam.libraries.no_root": "папка Steam не найдена",
    "steam.libraries.vdf_error": "не удалось прочитать libraryfolders.vdf: {error}",
    "steam.libraries.line": "{path} — игр: {games}",
    "steam.libraries.line_missing": "{path} — недоступна",
    "steam.libraries.missing_hint": "Библиотека недоступна: {paths}. Диск не подключён или путь изменился.",

    # --- диски ---
    "disks.library.title": "Диск: {path}",
    "disks.no_libraries": "библиотеки Steam не найдены",
    "disks.no_proc_mounts": "не удалось прочитать /proc/self/mounts",
    "disks.no_mount": "не удалось определить, на каком разделе лежит библиотека",
    "disks.value": "{fs} на {source}, свободно {free}",
    "disks.compat_line": "префиксы Proton: {path} ({fs})",
    "disks.ntfs_hint": (
        "Библиотека на NTFS. Это частая причина проблем с Proton: префиксы игр требуют "
        "Linux-прав и симлинков, игры не запускаются, теряются сохранения. Лучше держать "
        "игры на ext4/btrfs или вынести steamapps/compatdata на Linux-раздел симлинком."
    ),
    "disks.ntfs_windows_names_hint": (
        "Библиотека на NTFS с опцией windows_names: Proton не сможет создать файлы вида «c:» "
        "в префиксах, игры не запустятся. Уберите windows_names или вынесите "
        "steamapps/compatdata на Linux-раздел."
    ),
    "disks.ntfs_compat_moved_hint": (
        "Библиотека на NTFS, но префиксы Proton уже вынесены на Linux-раздел ({target}). "
        "Главное обойдено. Остаётся риск: после Windows с «быстрым запуском» диск может стать "
        "«грязным» и смонтироваться только для чтения."
    ),
    "disks.fat_hint": (
        "Библиотека на {fs}: нет симлинков и Linux-прав, Proton здесь работать не будет. "
        "Переформатируйте диск в ext4/btrfs или вынесите steamapps/compatdata на Linux-раздел."
    ),
    "disks.fat_compat_moved_hint": "Библиотека на {fs}, префиксы вынесены. Работать будет, но медленнее и без прав.",
    "disks.ro_hint": "Диск смонтирован только для чтения: игры не обновятся и не сохранятся.",
    "disks.not_writable_hint": "Нет прав на запись в библиотеку: Steam не сможет ставить и обновлять игры.",
    "disks.noexec_hint": "Диск смонтирован с noexec: игры с него запускаться не будут. Уберите noexec в /etc/fstab.",
    "disks.dirty_hint": (
        "Ядро сообщает, что NTFS-том «грязный» (Windows не завершилась нормально или включён быстрый "
        "запуск). Загрузите Windows, выключите «быстрый запуск» и сделайте chkdsk."
    ),
    "disks.dirty_unknown": "Журнал ядра недоступен, «грязный» ли том, проверить не удалось.",
    "disks.low_space_hint": "Мало места ({free}): обновления игр и кэш шейдеров могут не влезть.",

    # --- Proton ---
    "proton.no_steam": "Steam не найден",
    "proton.official.title": "Proton от Valve",
    "proton.official.none": "не установлен",
    "proton.official.leftovers": "остатки удалённых версий (пустые папки): {names}",
    "proton.official.none_hint": "Steam скачает Proton сам при первом запуске Windows-игры (Steam Play включён по умолчанию).",
    "proton.custom.title": "Сторонние сборки",
    "proton.custom.none": "нет",
    "proton.custom.no_ge_hint": (
        "Нет Proton-GE. Он чинит видео в катсценах и многие игры, которые не идут на "
        "официальном Proton. Проще всего поставить через ProtonUp-Qt."
    ),

    # --- утилиты ---
    "tools.found": "есть",
    "tools.no32_hint": "Нет 32-битной части ({pkg32}): в 32-битных играх утилита не сработает.",
    "tools.gamemode.title": "GameMode",
    "tools.gamemode.hint": "Во время игры переключает процессор в режим производительности. Запуск: gamemoderun %command%",
    "tools.mangohud.title": "MangoHud",
    "tools.mangohud.hint": "Оверлей с FPS, загрузкой и температурами. Запуск: mangohud %command%",
    "tools.gamescope.title": "gamescope",
    "tools.gamescope.hint": "Микрокомпозитор от Valve: масштабирование, ограничение FPS, HDR. Нужен не всем.",

    # --- настройки ---
    "tuning.governor.title": "Governor процессора",
    "tuning.governor.none": "cpufreq недоступен (виртуалка?)",
    "tuning.governor.driver": " (драйвер {driver})",
    "tuning.governor.powersave_hint": (
        "Процессор держит минимальную частоту, игры могут тормозить. GameMode включает "
        "performance на время игры автоматически."
    ),
    "tuning.governor.epp_power_hint": "Режим энергосбережения (EPP: power) режет частоты. Поставьте профиль «сбалансированный» или «производительность».",
    "tuning.max_map_count.title": "vm.max_map_count",
    "tuning.max_map_count.unreadable": "не удалось прочитать /proc/sys/vm/max_map_count",
    "tuning.max_map_count.low_hint": (
        "Мало: часть игр (CS2, Hogwarts Legacy, игры на Source 2 и др.) вылетает при загрузке. "
        "Рекомендуется {good}, как в SteamOS."
    ),
    "tuning.nofile.title": "Лимит открытых файлов",
    "tuning.nofile.value": "мягкий {soft}, жёсткий {hard}",
    "tuning.nofile.unlimited": "без ограничений",
    "tuning.nofile.low_hint": (
        "Жёсткий лимит меньше {good}: в Proton не будет работать esync. Задайте "
        "DefaultLimitNOFILE=1024:{good} в /etc/systemd/system.conf и user.conf."
    ),
}
