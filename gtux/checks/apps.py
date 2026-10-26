"""Группа: лаунчеры и помощники — Heroic, Lutris, Faugus, protontricks.

Они нужны не всем, поэтому отсутствие — не проблема (статус «ОК»), а установка предлагается
«по желанию» в «Исправить…». Пакетом дистрибутива — где он есть во всех поддерживаемых
дистрибутивах (Lutris, protontricks), иначе с Flathub с --user, без пароля (Heroic, Faugus).
Id на Flathub сверены по flathub.org/api/v2/appstream 2026-10-26.
"""

from __future__ import annotations

from gtux import packages
from gtux.i18n import t
from gtux.models import Action, Context, Status
from gtux.runner import check, result
from gtux.system import run, which

GROUP = "apps"

# id: (программы в PATH, id на Flathub, компонент пакета дистрибутива или None)
APPS = {
    "heroic": (("heroic",), "com.heroicgameslauncher.hgl", None),
    "lutris": (("lutris",), "net.lutris.Lutris", "lutris"),
    "faugus": (("faugus-launcher",), "io.github.Faugus.faugus-launcher", None),
    "protontricks": (("protontricks",), "com.github.Matoking.protontricks", "protontricks"),
}


def flatpak_apps(ctx: Context) -> set[str] | None:
    """Установленные Flatpak-приложения (системные и --user); None — flatpak не установлен."""
    if ctx.flatpak_apps is None and which("flatpak"):
        out = run(["flatpak", "list", "--app", "--columns=application"])
        ctx.flatpak_apps = set(out.stdout.split()) if out.returncode == 0 else set()
    return ctx.flatpak_apps


def _make_check(app_id: str):
    binaries, flatpak_id, comp = APPS[app_id]

    @check(app_id)
    def _check(ctx: Context):
        hint = t(f"apps.{app_id}.hint")
        if any(which(b) for b in binaries):
            return result(GROUP, app_id, Status.OK, value=t("apps.native"), hint=hint)
        if flatpak_id in (flatpak_apps(ctx) or set()):
            return result(GROUP, app_id, Status.OK, value=t("apps.flatpak"), hint=hint)
        names = packages.component(ctx, comp) if comp else None
        if names:
            action = Action("package", names[0], optional=True)
            fix = ctx.package_manager.install_command(names) if ctx.package_manager else None
        else:
            action = Action("flatpak_app", flatpak_id, optional=True)
            fix = f"flatpak install --user flathub {flatpak_id}"
        return result(GROUP, app_id, Status.OK, value=t("apps.missing"), hint=hint, fix=fix, actions=[action])

    return _check


CHECKS = [_make_check(app_id) for app_id in APPS]
