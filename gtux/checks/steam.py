"""Группа 5: Steam — установлен ли, как, и где лежат библиотеки игр."""

from __future__ import annotations

from pathlib import Path

from gtux import packages, vdf
from gtux.i18n import t
from gtux.models import Action, Context, Status
from gtux.runner import check, result
from gtux.system import CommandError, run, which

GROUP = "steam"

FLATPAK_ID = "com.valvesoftware.Steam"

# Где бывает папка Steam при разных способах установки.
HOME = Path.home()
ROOT_CANDIDATES = {
    "native": [HOME / ".local/share/Steam", HOME / ".steam/steam", HOME / ".steam/root"],
    "flatpak": [HOME / ".var/app" / FLATPAK_ID / ".local/share/Steam",
                HOME / ".var/app" / FLATPAK_ID / "data/Steam"],
    "snap": [HOME / "snap/steam/common/.local/share/Steam"],
}


def find_roots() -> list[tuple[str, Path]]:
    """[(способ, путь)] без дублей: ~/.steam/root обычно симлинк на ~/.local/share/Steam."""
    seen: set[Path] = set()
    roots = []
    for kind, candidates in ROOT_CANDIDATES.items():
        for p in candidates:
            if (p / "steamapps").is_dir():
                real = p.resolve()
                if real not in seen:
                    seen.add(real)
                    roots.append((kind, real))
    return roots


def read_libraries(root: Path) -> list[Path]:
    """Пути библиотек из steamapps/libraryfolders.vdf (сама папка Steam — тоже библиотека)."""
    data = vdf.loads((root / "steamapps/libraryfolders.vdf").read_text(errors="replace"))
    folders = data.get("libraryfolders", {})
    paths = [Path(v["path"]) for v in folders.values() if isinstance(v, dict) and "path" in v]
    return paths or [root]


def count_games(library: Path) -> int:
    return sum(1 for _ in (library / "steamapps").glob("appmanifest_*.acf"))


def _install_methods(ctx: Context) -> list[str]:
    methods = []
    names = packages.component(ctx, "steam")
    pkgs = packages.query(ctx, names) if names else None
    if pkgs and pkgs.get(names[0]):
        methods.append(t("steam.install.package", version=packages.strip_version(pkgs[names[0]])))
    if which("flatpak"):
        try:
            apps = run(["flatpak", "list", "--app", "--columns=application"]).stdout.split()
        except CommandError:
            apps = []
        if FLATPAK_ID in apps:
            methods.append("flatpak")
    if which("snap"):
        try:
            if run(["snap", "list", "steam"]).returncode == 0:
                methods.append("snap")
        except CommandError:
            pass
    return methods


@check("install")
def check_install(ctx: Context):
    ctx.steam_roots = find_roots()
    methods = _install_methods(ctx)
    if not methods and not ctx.steam_roots:
        hint = t("steam.install.not_found_hint")
        if ctx.package_manager and ctx.package_manager.family == "fedora":
            hint += " " + t("steam.install.fedora_hint")
        return result(GROUP, "install", Status.WARN, value=t("steam.install.not_found"),
                      hint=hint, **packages.fix_for(ctx, packages.component(ctx, "steam") or []))
    if not methods:
        methods.append(t("steam.install.other"))
    value = ", ".join(methods)
    if len(methods) > 1:
        return result(GROUP, "install", Status.WARN, value=value, hint=t("steam.install.several_hint"))
    return result(GROUP, "install", Status.OK, value=value)


@check("libraries")
def check_libraries(ctx: Context):
    if not ctx.steam_roots:
        return result(GROUP, "libraries", Status.UNKNOWN, value=t("steam.libraries.no_root"))
    libs: list[Path] = []
    for _, root in ctx.steam_roots:
        try:
            found = read_libraries(root)
        except (OSError, vdf.VDFError) as e:
            # Свежий Steam, который ещё ни разу не запускали, этого файла не имеет.
            return result(GROUP, "libraries", Status.UNKNOWN, value=str(root),
                          error=t("steam.libraries.vdf_error", error=e))
        libs += [p for p in found if p not in libs]
    ctx.steam_libraries = libs

    lines, missing = [], []
    for lib in libs:
        if (lib / "steamapps").is_dir():
            lines.append(t("steam.libraries.line", path=lib, games=count_games(lib)))
        else:
            missing.append(str(lib))
            lines.append(t("steam.libraries.line_missing", path=lib))
    value = "\n".join(lines)
    if missing:
        return result(GROUP, "libraries", Status.WARN, value=value,
                      hint=t("steam.libraries.missing_hint", paths=", ".join(missing)))
    return result(GROUP, "libraries", Status.OK, value=value)


def parse_flatpak_filesystems(text: str) -> list[str]:
    """Строка filesystems= из `flatpak info --show-permissions` -> список разрешённых путей."""
    for line in text.splitlines():
        if line.startswith("filesystems="):
            return [e for e in line.split("=", 1)[1].split(";") if e]
    return []


def path_allowed(path: Path, entries: list[str], home: Path = HOME) -> bool:
    for entry in entries:
        if entry.startswith("!"):
            continue  # явный запрет, нам он ничего не даёт
        base = entry.split(":", 1)[0]  # убираем :ro / :rw / :create
        if base == "host":  # host-os и host-etc дают только системные папки, не /mnt и не /home
            return True
        if base == "home":
            target = home
        elif base.startswith("~/"):
            target = home / base[2:]
        elif base.startswith("/"):
            target = Path(base)
        else:
            continue  # xdg-download и т.п. — к библиотекам игр отношения не имеют
        if path == target or target in path.parents:
            return True
    return False


@check("flatpak_access")
def check_flatpak_access(ctx: Context):
    """Steam из Flatpak видит только разрешённые папки: библиотека на другом диске без доступа = «нет места»."""
    flatpak_roots = [root for kind, root in ctx.steam_roots if kind == "flatpak"]
    if not flatpak_roots or not which("flatpak"):
        return []
    sandbox = HOME / ".var/app" / FLATPAK_ID
    outside = [lib for lib in ctx.steam_libraries if sandbox not in lib.parents and lib != sandbox]
    if not outside:
        return result(GROUP, "flatpak_access", Status.OK, value=t("steam.flatpak_access.inside"))
    out = run(["flatpak", "info", "--show-permissions", FLATPAK_ID])
    if out.returncode != 0:
        return result(GROUP, "flatpak_access", Status.UNKNOWN, error=out.stderr.strip() or None)
    entries = parse_flatpak_filesystems(out.stdout)
    blocked = [lib for lib in outside if not path_allowed(lib, entries)]
    if blocked:
        fix = " && ".join(f"flatpak override --user --filesystem={lib} {FLATPAK_ID}" for lib in blocked)
        return result(GROUP, "flatpak_access", Status.FAIL,
                      value=t("steam.flatpak_access.blocked", paths=", ".join(map(str, blocked))),
                      hint=t("steam.flatpak_access.blocked_hint"), fix=fix,
                      actions=[Action("flatpak_filesystem", str(lib), FLATPAK_ID) for lib in blocked])
    return result(GROUP, "flatpak_access", Status.OK, value=t("steam.flatpak_access.ok"))


CHECKS = [check_install, check_libraries, check_flatpak_access]
