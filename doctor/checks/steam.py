"""Группа 5: Steam — установлен ли, как, и где лежат библиотеки игр."""

from __future__ import annotations

from pathlib import Path

from doctor import packages, vdf
from doctor.i18n import t
from doctor.models import Context, Status
from doctor.runner import check, result
from doctor.system import CommandError, run, which

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


CHECKS = [check_install, check_libraries]
