"""Страница «Параметры запуска»: переключатели -> готовая строка для Steam."""

from __future__ import annotations

import os

from gi.repository import Adw, Gdk, Gtk

from doctor.checks.games import analyze_launch_options
from doctor.i18n import t
from doctor.launchopts import LaunchConfig, build
from doctor.system import which

# (поле LaunchConfig, программа, которая должна быть установлена)
WRAPPERS = [("gamemode", "gamemoderun"), ("mangohud", "mangohud"), ("gamescope", "gamescope")]
PROTON = ["dxvk_hud", "proton_log", "no_fsync", "no_esync", "wined3d"]


def monitor_size() -> tuple[int, int]:
    """Разрешение первого монитора в физических пикселях (для gamescope -W/-H)."""
    display = Gdk.Display.get_default()
    monitors = display.get_monitors() if display else None
    if not monitors or monitors.get_n_items() == 0:
        return 1920, 1080
    mon = monitors.get_item(0)
    geo, scale = mon.get_geometry(), mon.get_scale_factor()
    return geo.width * scale, geo.height * scale


class LaunchOptionsPage(Adw.PreferencesPage):
    def __init__(self, copy_func):
        super().__init__()
        self.copy_func = copy_func
        self.cfg = LaunchConfig()
        self.switches: dict[str, Adw.SwitchRow] = {}

        wrappers = Adw.PreferencesGroup(title=t("gui.launch.wrappers"), description=t("gui.launch.desc"))
        for field, binary in WRAPPERS:
            row = self._switch(field)
            if not which(binary):
                row.set_sensitive(False)
                row.set_subtitle(t(f"gui.launch.{field}.sub") + " · " + t("common.not_installed"))
            wrappers.add(row)

        w, h = monitor_size()
        self.gs_expander = Adw.ExpanderRow(title=t("gui.launch.gamescope_opts"), sensitive=False)
        self.gs_width = Adw.SpinRow.new_with_range(640, 7680, 1)
        self.gs_width.set_title(t("gui.launch.width"))
        self.gs_width.set_value(w)
        self.gs_height = Adw.SpinRow.new_with_range(480, 4320, 1)
        self.gs_height.set_title(t("gui.launch.height"))
        self.gs_height.set_value(h)
        self.gs_full = Adw.SwitchRow(title=t("gui.launch.fullscreen"), active=True)
        for r in (self.gs_width, self.gs_height, self.gs_full):
            self.gs_expander.add_row(r)
            r.connect("notify::value" if isinstance(r, Adw.SpinRow) else "notify::active", self._update)
        wrappers.add(self.gs_expander)
        self.add(wrappers)

        proton = Adw.PreferencesGroup(title=t("gui.launch.proton"))
        for field in PROTON:
            proton.add(self._switch(field))
        cpus = os.cpu_count() or 64
        self.cores = Adw.SpinRow.new_with_range(0, cpus, 1)
        self.cores.set_use_markup(False)
        self.cores.set_title(t("gui.launch.cpu_cores"))
        self.cores.set_subtitle(t("gui.launch.cpu_cores.sub"))
        self.cores.connect("notify::value", self._update)
        proton.add(self.cores)
        self.add(proton)

        args = Adw.PreferencesGroup(title=t("gui.launch.args"))
        self.args = Adw.EntryRow(title=t("gui.launch.args_placeholder"))
        self.args.connect("changed", self._update)
        args.add(self.args)
        self.add(args)

        out = Adw.PreferencesGroup(title=t("gui.launch.result"), description=t("gui.launch.where"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        line = Gtk.Box(spacing=8)
        self.result = Gtk.Label(xalign=0, wrap=True, selectable=True, hexpand=True)
        self.result.add_css_class("code")
        line.append(self.result)
        copy = Gtk.Button(label=t("gui.copy"), valign=Gtk.Align.CENTER)
        copy.add_css_class("pill")
        copy.add_css_class("suggested-action")
        copy.connect("clicked", lambda *_: self.copy_func(self.result.get_text()))
        line.append(copy)
        box.append(line)
        self.warnings = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.warnings.add_css_class("error-box")
        box.append(self.warnings)
        out.add(box)
        self.add(out)
        self._update()

    def _switch(self, field: str) -> Adw.SwitchRow:
        row = Adw.SwitchRow()
        row.set_use_markup(False)  # в подписях есть <appid> и %command% — разметку выключаем до текста
        row.set_title(t(f"gui.launch.{field}"))
        row.set_subtitle(t(f"gui.launch.{field}.sub"))
        row.connect("notify::active", self._update)
        self.switches[field] = row
        return row

    def _update(self, *_):
        for field, row in self.switches.items():
            setattr(self.cfg, field, row.get_active())
        self.gs_expander.set_sensitive(self.cfg.gamescope)
        self.cfg.gamescope_width = int(self.gs_width.get_value())
        self.cfg.gamescope_height = int(self.gs_height.get_value())
        self.cfg.gamescope_fullscreen = self.gs_full.get_active()
        self.cfg.cpu_cores = int(self.cores.get_value())
        self.cfg.game_args = self.args.get_text()
        try:
            text = build(self.cfg)
        except ValueError:
            self.warnings.set_text(t("gui.launch.bad_quotes"))
            self.warnings.set_visible(True)
            return
        self.result.set_text(text)
        problems = [hint for _, hint in analyze_launch_options(text)]
        self.warnings.set_text("\n".join(problems))
        self.warnings.set_visible(bool(problems))
