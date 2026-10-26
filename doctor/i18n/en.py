"""English UI texts. Keys must match ru.py (tests/test_i18n.py checks this)."""

TEXTS = {
    # --- common ---
    "app.title": "GTux",
    "app.subtitle": "Read-only check, nothing on your system is changed",
    "common.not_installed": "not installed",
    "common.crashed": "the check crashed",
    "common.gb": "{n} GB",
    "common.mb": "{n} MB",
    "status.ok": "OK",
    "status.warn": "COULD BE BETTER",
    "status.fail": "PROBLEM",
    "status.unknown": "NOT CHECKED",
    "ui.col.status": "Status",
    "ui.col.check": "Check",
    "ui.col.result": "Result",
    "ui.fix": "Fix: ",
    "ui.error": "Error: ",
    "ui.summary": "Total: OK {ok}, could be better {warn}, problems {fail}, not checked {unknown}",
    "ui.all_good": "No serious problems found.",
    "ui.has_problems": "There are problems: see the red rows above.",
    "ui.note": "Commands are only shown. Without --fix and your confirmation nothing is changed.",
    "ui.fix_hint": "Some problems can be fixed automatically: {cmd} --fix",
    "cli.description": "Checks your Linux system and explains what is missing for gaming.",
    "cli.json": "print the result as JSON (for scripts, bots, GUI)",
    "cli.lang": "interface language",
    "cli.fix": "fix what can be fixed automatically (asks for confirmation)",
    "cli.need_rich": (
        "The rich library for pretty output was not found.\n"
        "Install it (Arch: sudo pacman -S python-rich) or run with --json."
    ),

    # --- groups ---
    "group.distro": "System",
    "group.gpu": "Graphics card",
    "group.vulkan": "Vulkan",
    "group.multilib": "32-bit support",
    "group.steam": "Steam",
    "group.disks": "Game drives",
    "group.proton": "Proton",
    "group.tools": "Gaming tools",
    "group.tuning": "System settings",
    "group.games": "Games",

    # --- system ---
    "distro.os.title": "Distribution",
    "distro.os.no_file": "could not read /etc/os-release",
    "distro.os.based_on": " (based on {base})",
    "distro.kernel.title": "Kernel",
    "distro.kernel.unparsed": "could not parse the kernel version",
    "distro.kernel.old_hint": (
        "Kernel older than 5.16: it lacks futex_waitv, so Proton can't use fsync. "
        "Games will run, but sometimes slower. Update the system or install a newer kernel."
    ),
    "distro.package_manager.title": "Package manager",
    "distro.package_manager.none": "not found",
    "distro.package_manager.aur": ", AUR: {helpers}",
    "distro.package_manager.flatpak": ", flatpak available",
    "distro.package_manager.unsupported_hint": (
        "Packages can be checked with pacman, apt and dnf. "
        "This system uses another manager, so package checks are skipped."
    ),

    # --- graphics card ---
    "gpu.no_gpus": "no graphics cards found",
    "gpu.detect.title": "Graphics card",
    "gpu.detect.none": "not found",
    "gpu.detect.none_error": "no PCI graphics card in /sys/class/drm (virtual machine or container?)",
    "gpu.driver.title": "Driver",
    "gpu.driver.title_for": "Driver: {name}",
    "gpu.driver.unknown_vendor": "Unknown graphics card vendor (PCI vendor {vendor_id}).",
    "gpu.driver.not_loaded": "not loaded",
    "gpu.driver.not_loaded_hint": (
        "No driver is loaded for the graphics card. Without it there is no hardware acceleration "
        "and games won't start. How to install: {wiki}"
    ),
    "gpu.driver.nouveau_hint": (
        "The open-source nouveau driver is in use. For games it is usually much slower than the "
        "NVIDIA driver. Which NVIDIA package you need depends on the card generation: {wiki}"
    ),
    "gpu.driver.radeon_hint": (
        "The old radeon driver is in use. It has no Vulkan, so Proton/DXVK won't work. "
        "GCN 1.0/2.0 cards can be switched to amdgpu with kernel parameters: {wiki}"
    ),
    "gpu.driver.unexpected_hint": "An unusual driver is loaded. Check that it is the one you need: {wiki}",
    "gpu.nvidia_version.title": "NVIDIA driver version",
    "gpu.nvidia_version.no_sysfs": "/sys/module/nvidia/version is missing",
    "gpu.nvidia_version.mismatch": "loaded {loaded}, package {userspace}",
    "gpu.nvidia_version.mismatch_hint": (
        "The driver was updated but the computer hasn't been rebooted. Until then games and Vulkan "
        "may fail with a “version mismatch” error. Reboot."
    ),
    "gpu.mesa_version.title": "Mesa version",
    "gpu.rebar.title": "Resizable BAR",
    "gpu.rebar.title_for": "Resizable BAR: {name}",
    "gpu.rebar.on": "enabled",
    "gpu.rebar.off": "disabled",
    "gpu.rebar.value": "window {bar}, video memory {vram}",
    "gpu.rebar.no_bars": "could not read the card's BARs from /sys",
    "gpu.rebar.off_capable_hint": (
        "The card supports ReBAR but it is off. In UEFI enable “Above 4G Decoding” and "
        "“Re-Size BAR”, disable CSM. Gives more FPS in some games, especially on AMD."
    ),
    "gpu.rebar.unsupported_hint": (
        "The card or motherboard doesn't advertise ReBAR. A BIOS or GPU firmware update "
        "sometimes helps. Not critical."
    ),
    "gpu.mesa_version.not_found": "could not detect the Mesa version: no mesa package and no glxinfo",

    # --- Vulkan ---
    "vulkan.loader.title": "Vulkan loader",
    "vulkan.loader.missing_hint": "Without the Vulkan loader no Vulkan, DXVK or VKD3D game works (so neither does Proton).",
    "vulkan.icd.title": "Vulkan drivers (ICD)",
    "vulkan.icd.none": "not found",
    "vulkan.icd.missing_hint": (
        "No Vulkan driver for: {vendors}. Without it Proton games won't start "
        "or will run on the CPU."
    ),
    "vulkan.icd.packages": "Package needed: {packages}.",
    "vulkan.devices.title": "Vulkan sees the GPU",
    "vulkan.devices.no_tool": "vulkaninfo is missing",
    "vulkan.devices.no_tool_hint": "vulkaninfo is only needed for this check, games don't need it.",
    "vulkan.devices.failed": "vulkaninfo exited with an error",
    "vulkan.devices.failed_hint": "Vulkan failed to start. The driver is the usual cause, see the error below.",
    "vulkan.devices.cpu_only_hint": (
        "Vulkan only sees the software renderer on the CPU (llvmpipe). Games will be "
        "very slow or won't start. Check the graphics driver."
    ),
    "vulkan.devices.unseen_hint": "These cards are in the system but Vulkan doesn't see them: {gpus}.",

    # --- 32 bit ---
    "multilib.unsupported": "not checked on this distribution yet",
    "multilib.repo.title": "32-bit packages (multilib / i386)",
    "multilib.repo.i386_enabled": "i386 architecture enabled",
    "multilib.repo.i386_disabled": "i386 architecture disabled",
    "multilib.repo.i386_hint": "Without i386 you can't install 32-bit libraries, and Steam and many games need them.",
    "multilib.repo.fedora": ".i686 packages are always available",
    "multilib.repo.no_conf": "could not read {path}",
    "multilib.repo.enabled": "enabled",
    "multilib.repo.disabled": "disabled",
    "multilib.repo.disabled_hint": (
        "Without multilib you can't install 32-bit libraries, and Steam and many games need them. "
        "In {path} remove the # before [multilib] and the Include line below it, "
        "then refresh the package databases."
    ),
    "multilib.packages.title": "32-bit drivers and Vulkan",
    "multilib.packages.missing": "missing: {packages}",
    "multilib.packages.missing_hint": (
        "32-bit games and Steam itself won't see the GPU: crashes on launch "
        "or a “no Vulkan device” error."
    ),
    "multilib.packages.enable_first": "Enable 32-bit packages first (see the row above).",
    "multilib.packages.unknown_vendor": "The 32-bit driver for {vendors} isn't checked on this distribution.",
    "multilib.nvidia_match.title": "NVIDIA driver 64/32-bit versions",
    "multilib.nvidia_match.differ": "64-bit: {v64}, 32-bit: {v32}",
    "multilib.nvidia_match.differ_hint": (
        "The driver parts have different versions. 32-bit games may crash. "
        "A full system update usually fixes it."
    ),

    # --- Steam ---
    "steam.install.title": "Steam installation",
    "steam.install.package": "package {version}",
    "steam.install.other": "other (folder exists, no package)",
    "steam.install.not_found": "not found",
    "steam.install.not_found_hint": "Steam is not installed. If you play via Heroic or Lutris, that's fine.",
    "steam.install.fedora_hint": "On Fedora the steam package is in the RPM Fusion nonfree repository, enable it first.",
    "steam.install.several_hint": "Steam is installed in several ways. It's easy to mix up games and settings.",
    "steam.libraries.title": "Game libraries",
    "steam.libraries.no_root": "Steam folder not found",
    "steam.libraries.vdf_error": "could not read libraryfolders.vdf: {error}",
    "steam.libraries.line": "{path}: {games} games",
    "steam.libraries.line_missing": "{path}: unavailable",
    "steam.libraries.missing_hint": "Library unavailable: {paths}. The drive is not mounted or the path changed.",

    # --- drives ---
    "disks.library.title": "Drive: {path}",
    "disks.no_libraries": "no Steam libraries found",
    "disks.no_proc_mounts": "could not read /proc/self/mounts",
    "disks.no_mount": "could not tell which partition holds the library",
    "disks.value": "{fs} on {source}, {free} free",
    "disks.compat_line": "Proton prefixes: {path} ({fs})",
    "disks.ntfs_hint": (
        "The library is on NTFS. This is a common cause of Proton problems: game prefixes need "
        "Linux permissions and symlinks, so games fail to start and saves get lost. Keep games "
        "on ext4/btrfs, or symlink steamapps/compatdata to a Linux partition."
    ),
    "disks.ntfs_windows_names_hint": (
        "The library is on NTFS mounted with windows_names: Proton can't create files like “c:” "
        "in prefixes, so games won't start. Remove windows_names or move "
        "steamapps/compatdata to a Linux partition."
    ),
    "disks.ntfs_compat_moved_hint": (
        "The library is on NTFS, but Proton prefixes are already on a Linux partition ({target}). "
        "The main issue is avoided. Remaining risk: after Windows with “Fast Startup” the drive can be "
        "left “dirty” and mount read-only."
    ),
    "disks.fat_hint": (
        "The library is on {fs}: no symlinks or Linux permissions, Proton won't work here. "
        "Reformat the drive to ext4/btrfs or move steamapps/compatdata to a Linux partition."
    ),
    "disks.fat_compat_moved_hint": "The library is on {fs}, prefixes are moved. It works, but slower and without permissions.",
    "disks.ro_hint": "The drive is mounted read-only: games can't update or save.",
    "disks.not_writable_hint": "No write permission for the library: Steam can't install or update games.",
    "disks.noexec_hint": "The drive is mounted with noexec: games won't start from it. Remove noexec in /etc/fstab.",
    "disks.dirty_hint": (
        "The kernel reports the NTFS volume is “dirty” (Windows didn't shut down cleanly or Fast Startup "
        "is on). Boot Windows, disable Fast Startup and run chkdsk."
    ),
    "disks.dirty_unknown": "The kernel log is not readable, so a “dirty” volume could not be checked.",
    "disks.low_space_hint": "Low on space ({free}): game updates and the shader cache may not fit.",

    # --- Proton ---
    "proton.no_steam": "Steam not found",
    "proton.official.title": "Proton by Valve",
    "proton.official.none": "not installed",
    "proton.official.leftovers": "leftovers of removed versions (empty folders): {names}",
    "proton.official.none_hint": "Steam downloads Proton itself on the first launch of a Windows game (Steam Play is on by default).",
    "proton.custom.title": "Custom builds",
    "proton.custom.none": "none",
    "proton.custom.no_ge_hint": (
        "No Proton-GE. It fixes cutscene videos and many games that don't run on "
        "official Proton. The easiest way to get it is ProtonUp-Qt."
    ),

    # --- tools ---
    "tools.found": "installed",
    "tools.no32_hint": "The 32-bit part is missing ({pkg32}): the tool won't work in 32-bit games.",
    "tools.gamemode.title": "GameMode",
    "tools.gamemode.hint": "Switches the CPU to performance mode while you play. Usage: gamemoderun %command%",
    "tools.mangohud.title": "MangoHud",
    "tools.mangohud.hint": "Overlay with FPS, load and temperatures. Usage: mangohud %command%",
    "tools.gamescope.title": "gamescope",
    "tools.gamescope.hint": "Valve's micro-compositor: upscaling, FPS limit, HDR. Not everyone needs it.",

    # --- settings ---
    "tuning.governor.title": "CPU governor",
    "tuning.governor.none": "cpufreq unavailable (virtual machine?)",
    "tuning.governor.driver": " (driver {driver})",
    "tuning.governor.powersave_hint": (
        "The CPU stays at its minimum frequency, games may stutter. GameMode switches to "
        "performance automatically while you play."
    ),
    "tuning.governor.epp_power_hint": "The power-saving mode (EPP: power) limits clocks. Choose the “balanced” or “performance” profile.",
    "tuning.max_map_count.title": "vm.max_map_count",
    "tuning.max_map_count.unreadable": "could not read /proc/sys/vm/max_map_count",
    "tuning.max_map_count.low_hint": (
        "Too low: some games (CS2, Hogwarts Legacy, Source 2 games and others) crash while loading. "
        "{good} is recommended, as on SteamOS."
    ),
    "tuning.nofile.title": "Open files limit",
    "tuning.nofile.value": "soft {soft}, hard {hard}",
    "tuning.nofile.unlimited": "unlimited",
    "tuning.nofile.low_hint": (
        "The hard limit is below {good}: esync won't work in Proton. Set "
        "DefaultLimitNOFILE=1024:{good} in /etc/systemd/system.conf and user.conf."
    ),

    # --- install ---
    "fix.plan_title": "Fix plan:",
    "fix.kind.enable_i386": "enable the 32-bit architecture",
    "fix.kind.install": "install packages",
    "fix.kind.sysctl": "save a kernel setting",
    "fix.kind.flatpak_filesystem": "give Steam (Flatpak) access to a folder",
    "fix.skip.multilib": "Won't be installed automatically: {packages}. Enable [multilib] in /etc/pacman.conf first (see the table), then run --fix again.",
    "fix.nothing": "Nothing to fix automatically.",
    "fix.not_tty": "Input is not a terminal: nothing is executed. Run it in a terminal to confirm.",
    "fix.confirm": "Run it? [y] yes, [s] choose one by one, [Enter] cancel: ",
    "fix.confirm_short": "Run it? [y] yes, [Enter] cancel: ",
    "fix.ask_package": "  Install {package}? [y / Enter = no]: ",
    "fix.ask_step": "  {what} ({title})? [y / Enter = no]: ",
    "fix.cancelled": "Cancelled, nothing was changed.",
    "fix.done": "Done. Checking the system again:",
    "fix.reboot": "The driver was updated but the old one is still loaded: reboot the computer.",
    "fix.failed": "The command “{command}” exited with code {code}. The remaining steps were not run.",

    # --- games ---
    "games.list.title": "Games",
    "games.none": "no installed games",
    "games.runs.forced": "Runs with: {tool} (chosen in game properties)",
    "games.runs.native": "Runs with: native Linux version",
    "games.runs.default": "Runs with: default Proton ({tool})",
    "games.runs.default_steam": "Runs with: default Proton",
    "games.runs.tool_missing": "The selected build “{tool}” is not installed: the game won't start. Pick another one in Properties → Compatibility.",
    "games.launch.value": "Launch options: {opts}",
    "games.launch.quotes": "Unclosed quotes in the launch options.",
    "games.launch.no_command": "No %command% in the launch options: Steam passes them to the game as arguments, so variables and wrappers don't apply. Format: VARIABLE=1 gamemoderun %command%",
    "games.launch.missing_tool": "The launch options use {tool}, but it isn't installed: the game won't start.",
    "games.launch.topology_format": "WINE_CPU_TOPOLOGY={value} is malformed. Format: N:list of cores, where N equals their count, e.g. 4:0,1,2,3.",
    "games.launch.topology_cpus": "WINE_CPU_TOPOLOGY={value}: lists cores that don't exist (the system has {cpus}).",
    "games.launch.wined3d": "PROTON_USE_WINED3D=1 uses OpenGL instead of DXVK: usually much slower. Only needed for old GPUs.",
    "games.launch.proton_vars_native": "The game runs as a native Linux version, so PROTON_/DXVK_/WINE variables in its options have no effect.",
    "games.ac.supported": "Anti-cheat ({anticheats}) works on Linux",
    "games.ac.running": "Anti-cheat ({anticheats}): reported to work, not officially confirmed",
    "games.ac.planned": "Anti-cheat ({anticheats}): Linux support was promised, online may not work yet.",
    "games.ac.broken": "Anti-cheat ({anticheats}): online play on Linux is currently broken.",
    "games.ac.denied": "Anti-cheat ({anticheats}): the developers block Linux, online play doesn't work. This can't be fixed on our side.",
    "games.ac.online_broken": "Online mode doesn't work on Linux because of the anti-cheat.",
    "games.need_max_map_count": "The game needs vm.max_map_count ≥ {need}, current {have}: it may crash while loading (see “System settings”).",
    "games.protondb": "Player reports: https://www.protondb.com/app/{appid}",
    "games.ext.title": "{name} — {source}",
    "games.ext.runner": "Runs with: {runner}",
    "games.ext.runner_default": "launcher's default Wine/Proton",
    "games.ext.runner_missing": "The selected Wine/Proton “{runner}” was not found: the game won't start. Pick another one in the game settings.",
    "games.ext.no_install": "Game folder not found ({path}): the drive isn't mounted or the game was removed.",
    "games.ext.prefix_fs": "The Wine prefix is on {fs}: crashes and lost saves are possible. Move it to ext4/btrfs.",
    "games.ext.env": "Variables: {env}",

    # --- graphical window ---
    "cli.gui": "open the graphical window",
    "gui.need_gtk": "The window needs GTK4, libadwaita and PyGObject (Arch: sudo pacman -S gtk4 libadwaita python-gobject). Error: {error}",
    "gui.loading": "Checking your system…",
    "gui.loading_sub": "This usually takes a couple of seconds",
    "gui.refresh": "Check again",
    "gui.overview": "Overview",
    "gui.menu": "Menu",
    "gui.menu.language": "Language",
    "gui.menu.about": "About",
    "gui.hero.ok": "Your system is ready for gaming",
    "gui.hero.warn": "Everything works, but it could be better",
    "gui.hero.fail": "Problems found",
    "gui.hero.sub_ok": "No serious problems. Minor tips below.",
    "gui.hero.sub_fail": "Start with the red items: they most likely affect your games.",
    "gui.stat.ok": "OK",
    "gui.stat.warn": "could be better",
    "gui.stat.fail": "problems",
    "gui.stat.unknown": "not checked",
    "gui.todo.title": "What to do",
    "gui.todo.desc": "Most important first. Click an item to see the details.",
    "gui.todo.empty": "Nothing to do. Have a good game!",
    "gui.group.desc": "OK: {ok} · could be better: {warn} · problems: {fail} · not checked: {unknown}",
    "gui.fix.banner": "Can be fixed automatically: {count}",
    "gui.fix.button": "Fix…",
    "gui.fix.title": "Fix",
    "gui.fix.intro": "Tick what to fix. The system will ask for the administrator password once.",
    "gui.fix.root": "needs password",
    "gui.fix.skipped": "Won't be installed automatically: {packages}. Enable [multilib] in /etc/pacman.conf first.",
    "gui.fix.copy": "Copy commands",
    "gui.fix.install": "Apply",
    "gui.fix.running": "Fixing…",
    "gui.fix.done": "Done. Checking the system again.",
    "gui.fix.failed": "The command exited with code {code}. See the log below.",
    "gui.fix.no_pkexec": "pkexec was not found: copy the commands and run them in a terminal.",
    "gui.close": "Close",
    "gui.copy": "Copy",
    "gui.copied": "Copied",
    "gui.details.fix": "How to fix",
    "gui.details.error": "Error",
    "gui.crashed": "The check failed to run: {error}",
    "gui.about.comments": "Checks your Linux system and explains in plain words what is missing for gaming.",
    # --- new checks ---
    "group.hardware": "Hardware and devices",
    "gpu.modeset.title": "NVIDIA DRM modeset",
    "gpu.modeset.on": "enabled",
    "gpu.modeset.off": "disabled",
    "gpu.modeset.unreadable": "/sys/module/nvidia_drm/parameters/modeset is missing",
    "gpu.modeset.off_hint": "Without nvidia_drm.modeset=1, Wayland can show a black screen, stutter or a wrong refresh rate. Add the kernel parameter: {wiki}",
    "tuning.split_lock.title": "Split lock slowdown",
    "tuning.split_lock.on": "enabled",
    "tuning.split_lock.off": "disabled",
    "tuning.split_lock.on_hint": "The kernel deliberately slows programs that cause split locks, which makes some Windows games stutter. SteamOS and CachyOS disable it. Downside: the kernel stops throttling such programs.",
    "disks.hdd_hint": "The library is on a hard disk (HDD): long loading and texture pop-in in big games. If you have an SSD, keep games there.",
    "steam.flatpak_access.title": "Flatpak Steam drive access",
    "steam.flatpak_access.inside": "all libraries are inside the sandbox",
    "steam.flatpak_access.ok": "libraries are accessible",
    "steam.flatpak_access.blocked": "no access: {paths}",
    "steam.flatpak_access.blocked_hint": "Flatpak Steam can't see these folders: games “disappear” or won't install. Grant access with the command below (no sudo needed) and restart Steam.",
    "hardware.memory.title": "Memory and swap",
    "hardware.memory.value": "RAM {ram}, swap {swap}",
    "hardware.memory.no_swap": "none",
    "hardware.memory.unreadable": "could not read /proc/meminfo",
    "hardware.memory.low_ram_hint": "Less than {gb} GB of RAM: not enough for many modern games, expect crashes and stutter.",
    "hardware.memory.no_swap_hint": "No swap and no zram: when memory runs out, the game crashes or the system freezes. Enabling zram is the easiest fix (Arch: zram-generator package).",
    "hardware.audio.title": "Sound",
    "hardware.audio.none": "no sound server found",
    "hardware.audio.none_hint": "Neither PipeWire nor PulseAudio is running: games may have no sound. If you do have sound, ignore this.",
    "hardware.audio.no_pulse_hint": "PipeWire runs without pipewire-pulse: Steam and most games (via Wine) output sound through PulseAudio, so there will be no sound without the bridge.",
    "hardware.controllers.title": "Controllers (udev rules)",
    "hardware.controllers.none": "no rules for Steam controllers found",
    "hardware.controllers.none_hint": "Without udev rules the Steam Controller, Steam Deck, gamepads and VR headsets may not work without root.",
    # --- log, history, report ---
    "cli.report": "print a Markdown report for a forum or chat",
    "cli.debug": "verbose log to the terminal (it's always written to the file too)",
    "cli.no_history": "don't save this run to the check history",
    "cli.log_epilog": "Debug log: {path}",
    "cli.crashed": "The program crashed. Details are in the log: {path}",
    "history.title": "What changed since the last check ({when}):",
    "history.status": "{title}: {old} → {new}",
    "history.value": "{title}: {old} → {new}",
    "history.added": "{title}: new check",
    "history.removed": "{title}: no longer checked (removed?)",
    "report.title": "system report",
    "report.driver": "Driver",
    "report.summary": "Summary",
    "report.problems": "Problems and tips",
    "report.all_checks": "All checks",
    "report.footer": "Generated by GTux {version}, {date}",
    "gui.menu.log": "Open log",
    "gui.log.missing": "The log is empty so far",
    "gui.report.copy": "Copy report for a forum",
    "gui.report.copied": "Report copied: paste it into a forum or chat",
    "gui.changes.title": "What changed since the last check",
    "gui.launch.title": "Launch options",
    "gui.launch.desc": "Turn on what you need and a ready-made Steam line appears below.",
    "gui.launch.wrappers": "Wrappers",
    "gui.launch.proton": "Proton and DXVK",
    "gui.launch.args": "Game arguments",
    "gui.launch.args_placeholder": "Arguments after %command%, e.g. -novid",
    "gui.launch.result": "Ready-made line",
    "gui.launch.where": "Pick a game at the top and press “Write to Steam” (Steam must be closed). Or by hand: Steam → right-click the game → Properties → Launch options.",
    "gui.launch.bad_quotes": "Unclosed quotes in the game arguments.",
    "gui.launch.gamemode": "GameMode",
    "gui.launch.gamemode.sub": "CPU performance mode while you play",
    "gui.launch.mangohud": "MangoHud",
    "gui.launch.mangohud.sub": "Overlay with FPS, load and temperatures",
    "gui.launch.gamescope": "gamescope",
    "gui.launch.gamescope.sub": "Separate compositor: fullscreen, upscaling, FPS limit",
    "gui.launch.gamescope_opts": "gamescope settings",
    "gui.launch.width": "Width",
    "gui.launch.height": "Height",
    "gui.launch.fullscreen": "Fullscreen",
    "gui.launch.dxvk_hud": "DXVK FPS counter",
    "gui.launch.dxvk_hud.sub": "DXVK_HUD=fps: a simple counter without MangoHud (DirectX 9–11 games only)",
    "gui.launch.proton_log": "Proton log",
    "gui.launch.proton_log.sub": "PROTON_LOG=1: log to ~/steam-<appid>.log, the program can analyze crashes from it",
    "gui.launch.no_fsync": "Disable fsync",
    "gui.launch.no_fsync.sub": "PROTON_NO_FSYNC=1: only if the game hangs or crashes with it",
    "gui.launch.no_esync": "Disable esync",
    "gui.launch.no_esync.sub": "PROTON_NO_ESYNC=1: only if the game hangs or crashes with it",
    "gui.launch.wined3d": "OpenGL instead of Vulkan (WineD3D)",
    "gui.launch.wined3d.sub": "PROTON_USE_WINED3D=1: for old GPUs without Vulkan, usually much slower",
    "gui.launch.cpu_cores": "Limit CPU cores",
    "gui.launch.cpu_cores.sub": "WINE_CPU_TOPOLOGY: for old games that crash on many-core CPUs. 0 means no limit",
    "gui.launch.game": "Game",
    "gui.launch.game.desc": "Pick a Steam game: the app shows its options, player tips for your PC and can write the line straight into Steam.",
    "gui.launch.no_game": "No game — just build a line",
    "gui.launch.no_games": "No Steam games found",
    "gui.launch.now": "Currently in Steam",
    "gui.launch.now.empty": "no options set",
    "gui.launch.tier": "ProtonDB: {tier} ({total} reports)",
    "gui.launch.tips": "Player tips (ProtonDB)",
    "gui.launch.tips.desc": "From reports of the last 2 years, filtered for your PC ({gpu}, {session}). Common ones are already on — check before writing.",
    "gui.launch.tips.none": "Players don't suggest anything for this game that fits your PC.",
    "gui.launch.tip.count": "{count} of {total} reports ({who})",
    "gui.launch.tip.all": "all GPUs",
    "gui.launch.tip.build": "works only in {builds}, but the game runs with {tool}",
    "gui.launch.tip.experimental": "experimental, issues are possible",
    "gui.launch.tip.missing": "needs {tool}, which isn't installed",
    "gui.launch.tip.arg": "an argument for the game itself",
    "gui.launch.tip.already": "already in the options",
    "rec.title": "Recommendation for your PC",
    "rec.desc": "Based on ProtonDB player reports from the last year ({gpu}). Statistics, not a guarantee.",
    "rec.variant.official": "Proton (official)",
    "rec.variant.experimental": "Proton Experimental",
    "rec.variant.ge": "GE-Proton",
    "rec.variant.older": "an older Proton version",
    "rec.variant.native": "native Linux version, no Proton",
    "rec.proton": "Build: {name}",
    "rec.stat": "works in {works} of {total} reports ({who})",
    "rec.close": "other builds are almost as good",
    "rec.use": "choose {name}",
    "rec.current_ok": "already selected in Steam",
    "rec.current": "currently in Steam: {tool}",
    "rec.cachyos": "ProtonDB has no separate statistics for proton-cachyos: if the game runs well for you, no need to change",
    "rec.missing.ge": "not installed: get it with ProtonUp-Qt or ProtonPlus (both on Flathub)",
    "rec.missing.valve": "Steam downloads it when you select it",
    "rec.versions": "most often working: {versions}",
    "rec.how": "How: Steam → right-click the game → Properties → Compatibility",
    "rec.how_native": "How: Steam → right-click the game → Properties → Compatibility → uncheck “Force the use of…”",
    "rec.others": "Other builds",
    "rec.others.item": "{name}: {works} of {total}",
    "rec.broken": "Barely runs for anyone",
    "rec.broken.sub": "works in {works} of {total} reports ({who}): switching builds is unlikely to help, check anti-cheat in the Games section",
    "rec.few": "Not enough reports to pick a build",
    "rec.few.sub": "fewer than {min} reports per build from players with a similar PC",
    "rec.kb_old": "The knowledge base has no Proton build data yet",
    "rec.kb_old.sub": "Update the knowledge base (menu → Update the knowledge base)",
    "rec.opts": "Launch options",
    "rec.opts.on": "player tips enabled: {tips}. The final line is at the bottom of the page",
    "rec.opts.none": "no extra options needed",
    "games.rec": "Best build among players with a similar PC: {name} ({works} of {total} reports)",
    "games.rec.broken": "Barely runs for players with a similar PC ({works} of {total} reports)",
    "gui.launch.kb_missing": "The knowledge base hasn't been downloaded yet",
    "gui.launch.kb_missing.sub": "About 70 MB from GitHub (ProtonDB reports), 1–3 minutes",
    "gui.launch.kept": "Keep from the current options",
    "gui.launch.kept.desc": "What the game already has in Steam. Turn a switch off to remove it.",
    "gui.launch.write": "Write to Steam",
    "gui.launch.undo": "Undo",
    "gui.launch.written": "Options for “{name}” written. A copy of the old file was saved.",
    "gui.launch.undone": "The previous options are back.",
    "gui.launch.steam_running": "Steam is running. Close it (Steam → Exit), otherwise it overwrites the options on exit, and press again.",
    "gui.launch.write_failed": "Couldn't write: {error}",
    "gui.launch.complex": "The game's current options are more complex than the app can safely change (shell commands or unknown programs). Copy the line and edit it by hand.",
    "gui.launch.args_complex": "The game arguments contain shell characters (; | & $): the app won't write such a line to Steam.",
    "gui.kb.update": "Update the knowledge base",
    "gui.kb.title": "Knowledge base",
    "gui.kb.intro": "The app downloads ProtonDB player reports (about 70 MB from GitHub, updated monthly) and ratings of your games from protondb.com. It uses them to pick launch options for your PC. Takes 1–3 minutes, after that everything works offline.",
    "gui.kb.current": "Current: from {when} ({dump})",
    "gui.kb.never": "Not downloaded yet.",
    "gui.kb.start": "Download",
    "gui.kb.mb": "{done} / {total} MB",
    "gui.kb.stage.list": "Looking for the latest export…",
    "gui.kb.stage.download": "Downloading reports…",
    "gui.kb.stage.parse": "Reading reports (1–2 minutes)…",
    "gui.kb.stage.tiers": "Getting game ratings from ProtonDB…",
    "gui.kb.failed": "Failed: {error}",
    "gui.kb.done": "Knowledge base updated: tips for {games} games.",
    "games.tier": "ProtonDB: {tier} ({total} reports)",
    "games.tips": "Players with a similar PC suggest: {tips} (Launch options → pick the game)",
    "cli.update_kb": "download the ProtonDB knowledge base for launch option tips (needs internet)",
    "kb.intro": "Downloading ProtonDB reports (about 70 MB) and ratings of your games…",
    "group.logs": "Proton logs",
    "logs.proton.title": "Proton logs",
    "logs.title_for": "Log: {name}",
    "logs.none": "no logs. If a game crashes, enable PROTON_LOG=1 (see “Launch options”), run it and check again",
    "logs.value": "{path}, {date}, {size} MB",
    "logs.clean": "no known errors found",
    "logs.missing_dll": "The game is missing Windows libraries: {dlls}. They can be installed into the game prefix with protontricks (command below, if the library is known).",
    "logs.broken_prefix": "Wine couldn't load its system libraries: the game prefix looks broken. Back up your saves from steamapps/compatdata/{appid} and delete that folder: Steam will recreate the prefix.",
    "logs.device_lost": "The graphics driver lost the device (VK_ERROR_DEVICE_LOST): the GPU hung and reset. Causes: overclocking, overheating, running out of VRAM or a driver bug.",
    "logs.crash": "The game crashed inside Wine (Unhandled exception). Try another Proton version: Experimental or GE.",
}
