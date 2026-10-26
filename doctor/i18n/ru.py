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
    "ui.note": "Команды только показаны. Без --fix и вашего подтверждения программа ничего не меняет.",
    "ui.fix_hint": "Недостающие пакеты можно поставить так: python main.py --fix",
    "cli.description": "Проверяет Linux-систему и объясняет, чего не хватает для игр.",
    "cli.json": "вывести результат в JSON (для скриптов, бота, GUI)",
    "cli.lang": "язык интерфейса",
    "cli.fix": "предложить установку недостающих пакетов (спросит подтверждение)",
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
    "group.games": "Игры",

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

    # --- установка ---
    "fix.plan_title": "План исправления:",
    "fix.kind.enable_i386": "включить 32-битную архитектуру",
    "fix.kind.install": "установить пакеты",
    "fix.skip.multilib": "Не будут установлены автоматически: {packages}. Сначала включите [multilib] в /etc/pacman.conf (см. таблицу), потом запустите --fix ещё раз.",
    "fix.nothing": "Нечего устанавливать автоматически.",
    "fix.not_tty": "Ввод не из терминала: ничего не выполняю. Запустите в терминале, чтобы подтвердить.",
    "fix.confirm": "Выполнить? [д/y] да, [в/s] выбрать пакеты, [Enter] отмена: ",
    "fix.confirm_short": "Выполнить? [д/y] да, [Enter] отмена: ",
    "fix.ask_package": "  Ставить {package}? [д/y / Enter — нет]: ",
    "fix.cancelled": "Отменено, ничего не менялось.",
    "fix.done": "Готово. Запустите проверку ещё раз: python main.py",
    "fix.failed": "Команда «{command}» завершилась с кодом {code}. Остальные шаги не выполнялись.",

    # --- игры ---
    "games.list.title": "Игры",
    "games.none": "установленных игр нет",
    "games.runs.forced": "Запуск: {tool} (выбран в свойствах игры)",
    "games.runs.native": "Запуск: Linux-версия",
    "games.runs.default": "Запуск: Proton по умолчанию ({tool})",
    "games.runs.default_steam": "Запуск: Proton по умолчанию",
    "games.runs.tool_missing": "Выбранная сборка «{tool}» не установлена: игра не запустится. Выберите другую в Свойства → Совместимость.",
    "games.launch.value": "Параметры: {opts}",
    "games.launch.quotes": "В параметрах запуска не закрыты кавычки.",
    "games.launch.no_command": "В параметрах нет %command%: Steam передаст их игре как аргументы, переменные и обёртки не сработают. Формат: ПЕРЕМЕННАЯ=1 gamemoderun %command%",
    "games.launch.missing_tool": "В параметрах есть {tool}, но он не установлен: игра не запустится.",
    "games.launch.topology_format": "WINE_CPU_TOPOLOGY={value} записан неверно. Формат: N:список ядер, и N равно их количеству, например 4:0,1,2,3.",
    "games.launch.topology_cpus": "WINE_CPU_TOPOLOGY={value}: указаны ядра, которых нет (в системе {cpus}).",
    "games.launch.wined3d": "PROTON_USE_WINED3D=1 включает OpenGL вместо DXVK: обычно намного медленнее. Нужен только для старых видеокарт.",
    "games.launch.proton_vars_native": "Игра запускается в Linux-версии, поэтому переменные PROTON_/DXVK_/WINE в параметрах ни на что не влияют.",
    "games.ac.supported": "Античит ({anticheats}) работает на Linux",
    "games.ac.running": "Античит ({anticheats}): по отзывам работает, официально не подтверждено",
    "games.ac.planned": "Античит ({anticheats}): поддержку Linux обещали, но пока онлайн может не работать.",
    "games.ac.broken": "Античит ({anticheats}): онлайн на Linux сейчас сломан.",
    "games.ac.denied": "Античит ({anticheats}): разработчики не пускают Linux, онлайн не работает. Исправить на нашей стороне нельзя.",
    "games.ac.online_broken": "Онлайн-режим не работает на Linux из-за античита.",
    "games.need_max_map_count": "Игре нужен vm.max_map_count ≥ {need}, сейчас {have}: возможны вылеты при загрузке (см. «Настройки системы»).",
    "games.protondb": "Отзывы игроков: https://www.protondb.com/app/{appid}",
    "games.ext.title": "{name} — {source}",
    "games.ext.runner": "Запуск: {runner}",
    "games.ext.runner_default": "Wine/Proton по умолчанию лаунчера",
    "games.ext.runner_missing": "Выбранный Wine/Proton «{runner}» не найден: игра не запустится. Выберите другой в настройках игры.",
    "games.ext.no_install": "Папка игры не найдена ({path}): диск не подключён или игру удалили.",
    "games.ext.prefix_fs": "Префикс Wine лежит на {fs}: возможны вылеты и потеря сохранений. Перенесите его на ext4/btrfs.",
    "games.ext.env": "Переменные: {env}",

    # --- графическое окно ---
    "cli.gui": "открыть графическое окно",
    "gui.need_gtk": "Для окна нужны GTK4, libadwaita и PyGObject (Arch: sudo pacman -S gtk4 libadwaita python-gobject). Ошибка: {error}",
    "gui.loading": "Проверяю систему…",
    "gui.loading_sub": "Обычно это занимает пару секунд",
    "gui.refresh": "Проверить снова",
    "gui.overview": "Обзор",
    "gui.menu": "Меню",
    "gui.menu.language": "Язык",
    "gui.menu.about": "О программе",
    "gui.hero.ok": "Система готова к играм",
    "gui.hero.warn": "Всё работает, но можно лучше",
    "gui.hero.fail": "Найдены проблемы",
    "gui.hero.sub_ok": "Серьёзных проблем нет. Мелкие советы ниже.",
    "gui.hero.sub_fail": "Начните с красных пунктов: они скорее всего мешают играм.",
    "gui.stat.ok": "в порядке",
    "gui.stat.warn": "можно лучше",
    "gui.stat.fail": "проблемы",
    "gui.stat.unknown": "не проверено",
    "gui.todo.title": "Что стоит сделать",
    "gui.todo.desc": "Сначала самое важное. Нажмите, чтобы открыть подробности.",
    "gui.todo.empty": "Делать ничего не нужно. Хорошей игры!",
    "gui.group.desc": "в порядке: {ok} · можно лучше: {warn} · проблем: {fail} · не проверено: {unknown}",
    "gui.fix.banner": "Недостающее можно поставить автоматически (пакетов: {count})",
    "gui.fix.button": "Исправить…",
    "gui.fix.title": "Исправление",
    "gui.fix.intro": "Программа выполнит эти команды. Пароль администратора спросит система.",
    "gui.fix.skipped": "Не будут установлены автоматически: {packages}. Сначала включите [multilib] в /etc/pacman.conf.",
    "gui.fix.copy": "Скопировать команды",
    "gui.fix.install": "Установить",
    "gui.fix.running": "Устанавливаю…",
    "gui.fix.done": "Готово. Проверяю систему заново.",
    "gui.fix.failed": "Команда завершилась с кодом {code}. Подробности в журнале ниже.",
    "gui.fix.no_pkexec": "Не найден pkexec: скопируйте команды и выполните их в терминале.",
    "gui.close": "Закрыть",
    "gui.copy": "Скопировать",
    "gui.copied": "Скопировано",
    "gui.details.fix": "Как исправить",
    "gui.details.error": "Ошибка",
    "gui.crashed": "Проверка не запустилась: {error}",
    "gui.about.comments": "Проверяет Linux-систему и простым языком объясняет, чего не хватает для игр.",
    # --- новые проверки ---
    "group.hardware": "Железо и устройства",
    "gpu.modeset.title": "NVIDIA DRM modeset",
    "gpu.modeset.on": "включён",
    "gpu.modeset.off": "выключен",
    "gpu.modeset.unreadable": "нет /sys/module/nvidia_drm/parameters/modeset",
    "gpu.modeset.off_hint": "Без nvidia_drm.modeset=1 на Wayland бывают чёрный экран, рывки и неверная частота экрана. Добавьте параметр ядра: {wiki}",
    "tuning.split_lock.title": "Замедление split lock",
    "tuning.split_lock.on": "включено",
    "tuning.split_lock.off": "выключено",
    "tuning.split_lock.on_hint": "Ядро намеренно тормозит программы со split lock, от этого подтормаживают некоторые Windows-игры. В SteamOS и CachyOS это выключено. Минус: ядро перестанет сдерживать такие программы.",
    "disks.hdd_hint": "Библиотека на жёстком диске (HDD): долгие загрузки и подгрузки текстур в больших играх. Если есть SSD, лучше держать игры на нём.",
    "steam.flatpak_access.title": "Доступ Flatpak-Steam к дискам",
    "steam.flatpak_access.inside": "все библиотеки внутри песочницы",
    "steam.flatpak_access.ok": "доступ к библиотекам есть",
    "steam.flatpak_access.blocked": "нет доступа: {paths}",
    "steam.flatpak_access.blocked_hint": "Steam из Flatpak не видит эти папки: игры «пропадают» или не ставятся. Дайте доступ командой ниже (sudo не нужен) и перезапустите Steam.",
    "hardware.memory.title": "Память и swap",
    "hardware.memory.value": "ОЗУ {ram}, swap {swap}",
    "hardware.memory.no_swap": "нет",
    "hardware.memory.unreadable": "не удалось прочитать /proc/meminfo",
    "hardware.memory.low_ram_hint": "Меньше {gb} ГБ памяти: многим современным играм этого мало, возможны вылеты и подгрузки.",
    "hardware.memory.no_swap_hint": "Нет ни swap, ни zram: когда память кончится, игра вылетит или система зависнет. Проще всего включить zram (на Arch: пакет zram-generator).",
    "hardware.audio.title": "Звук",
    "hardware.audio.none": "звуковой сервер не найден",
    "hardware.audio.none_hint": "Не запущены ни PipeWire, ни PulseAudio: в играх может не быть звука. Если звук есть, можно не обращать внимания.",
    "hardware.audio.no_pulse_hint": "PipeWire работает без pipewire-pulse: Steam и большинство игр (через Wine) выводят звук через PulseAudio, без моста звука не будет.",
    "hardware.controllers.title": "Геймпады (правила udev)",
    "hardware.controllers.none": "правила для контроллеров Steam не найдены",
    "hardware.controllers.none_hint": "Без udev-правил Steam Controller, Steam Deck, геймпады и VR-шлемы могут не работать без root.",
    # --- журнал, история, отчёт ---
    "cli.report": "вывести отчёт в Markdown для форума или чата",
    "cli.debug": "подробный журнал в терминал (он всегда пишется и в файл)",
    "cli.no_history": "не сохранять результат в историю проверок",
    "cli.log_epilog": "Отладочный журнал: {path}",
    "cli.crashed": "Программа упала. Подробности в журнале: {path}",
    "history.title": "Что изменилось с прошлой проверки ({when}):",
    "history.status": "{title}: {old} → {new}",
    "history.value": "{title}: {old} → {new}",
    "history.added": "{title}: новая проверка",
    "history.removed": "{title}: больше не проверяется (удалено?)",
    "report.title": "отчёт о системе",
    "report.driver": "Драйвер",
    "report.summary": "Итого",
    "report.problems": "Проблемы и советы",
    "report.all_checks": "Все проверки",
    "report.footer": "Сделано программой «Доктор Linux-геймера» {version}, {date}",
    "gui.menu.log": "Открыть журнал",
    "gui.log.missing": "Журнал пока пуст",
    "gui.report.copy": "Скопировать отчёт для форума",
    "gui.report.copied": "Отчёт скопирован: вставьте его на форум или в чат",
    "gui.changes.title": "Что изменилось с прошлой проверки",
    "gui.launch.title": "Параметры запуска",
    "gui.launch.desc": "Включите нужное, и внизу появится готовая строка для Steam.",
    "gui.launch.wrappers": "Обёртки",
    "gui.launch.proton": "Proton и DXVK",
    "gui.launch.args": "Аргументы игры",
    "gui.launch.args_placeholder": "Аргументы после %command%, например -novid",
    "gui.launch.result": "Готовая строка",
    "gui.launch.where": "Steam → правый клик по игре → Свойства → Параметры запуска. Вставьте строку целиком.",
    "gui.launch.bad_quotes": "В аргументах игры не закрыты кавычки.",
    "gui.launch.gamemode": "GameMode",
    "gui.launch.gamemode.sub": "Режим производительности процессора на время игры",
    "gui.launch.mangohud": "MangoHud",
    "gui.launch.mangohud.sub": "Оверлей с FPS, загрузкой и температурами",
    "gui.launch.gamescope": "gamescope",
    "gui.launch.gamescope.sub": "Отдельный композитор: полный экран, масштабирование, ограничение FPS",
    "gui.launch.gamescope_opts": "Настройки gamescope",
    "gui.launch.width": "Ширина",
    "gui.launch.height": "Высота",
    "gui.launch.fullscreen": "Полный экран",
    "gui.launch.dxvk_hud": "Счётчик FPS от DXVK",
    "gui.launch.dxvk_hud.sub": "DXVK_HUD=fps: простой счётчик без MangoHud (только игры на DirectX 9–11)",
    "gui.launch.proton_log": "Журнал Proton",
    "gui.launch.proton_log.sub": "PROTON_LOG=1: лог в ~/steam-<appid>.log, по нему программа разберёт вылеты",
    "gui.launch.no_fsync": "Отключить fsync",
    "gui.launch.no_fsync.sub": "PROTON_NO_FSYNC=1: только если игра с ним зависает или падает",
    "gui.launch.no_esync": "Отключить esync",
    "gui.launch.no_esync.sub": "PROTON_NO_ESYNC=1: только если игра с ним зависает или падает",
    "gui.launch.wined3d": "OpenGL вместо Vulkan (WineD3D)",
    "gui.launch.wined3d.sub": "PROTON_USE_WINED3D=1: для старых видеокарт без Vulkan, обычно намного медленнее",
    "gui.launch.cpu_cores": "Ограничить число ядер",
    "gui.launch.cpu_cores.sub": "WINE_CPU_TOPOLOGY: для старых игр, которые падают на многоядерных процессорах. 0 — без ограничения",
}
