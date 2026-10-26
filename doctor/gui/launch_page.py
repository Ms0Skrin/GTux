"""Страница «Параметры запуска»: выбор игры, советы игроков под этот ПК, переключатели ->
готовая строка, которую можно записать прямо в Steam (с копией файла и откатом)."""

from __future__ import annotations

import os

from gi.repository import Adw, Gdk, Gtk

from doctor import knowledge, steamcfg
from doctor.checks.games import analyze_launch_options
from doctor.gamedb import SteamSettings
from doctor.i18n import t
from doctor.launchopts import LaunchConfig, Parsed, build, compose, config_from, merge, parse
from doctor.system import which

# (поле LaunchConfig, программа, которая должна быть установлена)
WRAPPERS = [("gamemode", "gamemoderun"), ("mangohud", "mangohud"), ("gamescope", "gamescope")]
PROTON = ["dxvk_hud", "proton_log", "no_fsync", "no_esync", "wined3d"]
PRESELECT_SHARE = 0.25  # советы, которые встречаются хотя бы в четверти отчётов, включаем сразу
# Обе включают режим производительности: сразу включаем только одну, ту, что популярнее у игроков.
PERF_WRAPPERS = {"gamemoderun", "game-performance"}


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
    def __init__(self, copy_func, toast_func=None, games: list[SteamSettings] | None = None,
                 profile: knowledge.Profile | None = None, update_kb=None):
        super().__init__()
        self.copy_func = copy_func
        self.toast = toast_func or (lambda text: None)
        self.games = games or []
        self.profile = profile
        self.update_kb = update_kb
        self.cfg = LaunchConfig()
        self.switches: dict[str, Adw.SwitchRow] = {}
        self.kept: list[tuple[Adw.SwitchRow, Parsed]] = []   # что оставить из текущих параметров
        self.tips: list[tuple[Adw.SwitchRow, Parsed]] = []   # советы игроков
        self.current: SteamSettings | None = None
        self.loading = False  # пока переключатели выставляются из Steam, строку не пересчитываем
        self.base_ok = True   # текущую строку игры удалось разобрать
        self.kb_row: Adw.ActionRow | None = None

        self._build_game_group()
        self.tips_group = Adw.PreferencesGroup(title=t("gui.launch.tips"), visible=False)
        self.add(self.tips_group)
        self.kept_group = Adw.PreferencesGroup(title=t("gui.launch.kept"), description=t("gui.launch.kept.desc"),
                                               visible=False)
        self.add(self.kept_group)

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

        self.out = Adw.PreferencesGroup(title=t("gui.launch.result"), description=t("gui.launch.where"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        line = Gtk.Box(spacing=8)
        self.result = Gtk.Label(xalign=0, wrap=True, selectable=True, hexpand=True)
        self.result.add_css_class("code")
        line.append(self.result)
        copy = Gtk.Button(label=t("gui.copy"), valign=Gtk.Align.CENTER)
        copy.add_css_class("pill")
        copy.connect("clicked", lambda *_: self.copy_func(self.result.get_text()))
        line.append(copy)
        box.append(line)
        buttons = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        self.undo_btn = Gtk.Button(label=t("gui.launch.undo"), visible=False)
        self.undo_btn.add_css_class("pill")
        self.undo_btn.connect("clicked", lambda *_: self._undo())
        buttons.append(self.undo_btn)
        self.write_btn = Gtk.Button(label=t("gui.launch.write"), visible=False)
        self.write_btn.add_css_class("pill")
        self.write_btn.add_css_class("suggested-action")
        self.write_btn.connect("clicked", lambda *_: self._write())
        buttons.append(self.write_btn)
        box.append(buttons)
        self.warnings = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.warnings.add_css_class("error-box")
        box.append(self.warnings)
        self.out.add(box)
        self.add(self.out)
        self._update()

    # ----- выбор игры -----
    def _build_game_group(self):
        group = Adw.PreferencesGroup(title=t("gui.launch.game"), description=t("gui.launch.game.desc"))
        names = [t("gui.launch.no_game")] + [s.game.name for s in self.games]
        self.game_row = Adw.ComboRow(title=t("gui.launch.game"), model=Gtk.StringList.new(names))
        self.game_row.set_use_markup(False)
        self.game_row.connect("notify::selected", lambda *_: self._on_game())
        group.add(self.game_row)
        self.now_row = Adw.ActionRow(title=t("gui.launch.now"), visible=False, subtitle_selectable=True)
        self.now_row.set_use_markup(False)
        group.add(self.now_row)
        if not self.games:
            self.game_row.set_sensitive(False)
            self.game_row.set_subtitle(t("gui.launch.no_games"))
        self.add(group)

    def _on_game(self):
        idx = self.game_row.get_selected()
        self.current = self.games[idx - 1] if 0 < idx <= len(self.games) else None
        self.loading = True
        try:
            self._load_current()
            self._fill_tips()
        finally:
            self.loading = False
        self._update()

    def _load_current(self):
        for row, _ in self.kept:
            self.kept_group.remove(row)
        self.kept.clear()
        s = self.current
        self.now_row.set_visible(s is not None)
        self.kept_group.set_visible(False)
        cfg = LaunchConfig()
        self.base_ok = True
        if s is not None:
            self.now_row.set_subtitle(s.options or t("gui.launch.now.empty"))
            parsed = parse(s.options) if s.options else Parsed()
            if parsed is None:
                self.base_ok = False  # сложная строка: не трогаем, только показываем
            else:
                cfg, rest = config_from(parsed)
                for p in self._split(rest):
                    row = Adw.SwitchRow(title=compose(p).replace(" %command%", ""), active=True)
                    row.set_use_markup(False)
                    row.connect("notify::active", self._update)
                    self.kept_group.add(row)
                    self.kept.append((row, p))
                self.kept_group.set_visible(bool(self.kept))
        for field, row in self.switches.items():
            row.set_active(bool(getattr(cfg, field)))
        self.cores.set_value(cfg.cpu_cores)
        self.args.set_text(cfg.game_args)

    @staticmethod
    def _split(p: Parsed) -> list[Parsed]:
        """Остаток текущей строки — по одному переключателю на переменную/обёртку."""
        parts = [Parsed(env={k: v}) for k, v in p.env.items()]
        if p.gamescope:
            parts.append(Parsed(gamescope=p.gamescope))
        parts += [Parsed(wrappers=[w]) for w in p.wrappers]
        return parts

    def _fill_tips(self):
        for row, _ in self.tips:
            self.tips_group.remove(row)
        self.tips.clear()
        if self.kb_row is not None:
            self.tips_group.remove(self.kb_row)
            self.kb_row = None
        s = self.current
        self.tips_group.set_visible(s is not None)
        if s is None:
            return
        data = knowledge.load()
        tier = knowledge.tier_for(s.game.appid, data)
        sub = t("gui.launch.tier", tier=tier["tier"], total=tier.get("total") or 0) if tier and tier.get("tier") else ""
        self.game_row.set_subtitle(sub)
        if not data:
            self.kb_row = Adw.ActionRow(title=t("gui.launch.kb_missing"), subtitle=t("gui.launch.kb_missing.sub"))
            if self.update_kb:
                btn = Gtk.Button(label=t("gui.kb.update"), valign=Gtk.Align.CENTER)
                btn.add_css_class("pill")
                btn.connect("clicked", lambda *_: self.update_kb())
                self.kb_row.add_suffix(btn)
            self.tips_group.add(self.kb_row)
            self.tips_group.set_description("")
            return
        prof = self.profile or knowledge.Profile("other", False, frozenset())
        tips = knowledge.tips_for(s.game.appid, prof, data)
        self.tips_group.set_description(
            t("gui.launch.tips.desc", gpu=prof.vendor.upper() if prof.vendor != "other" else "?",
              session="Wayland" if prof.wayland else "X11") if tips else t("gui.launch.tips.none"))
        current = parse(s.options) if s.options else Parsed()
        perf_on = current is not None and bool(PERF_WRAPPERS & set(current.wrappers))
        for tip in tips:
            sub = [t("gui.launch.tip.count", count=tip.count, total=tip.reports,
                     who=prof.vendor.upper() if tip.same_vendor else t("gui.launch.tip.all"))]
            fits = knowledge.works_with(tip, s.tool)
            if not fits:
                sub.append(t("gui.launch.tip.build", builds=", ".join(knowledge.BUILD_NAMES[b] for b in tip.builds),
                             tool=s.tool or "Proton"))
            if tip.experimental:
                sub.append(t("gui.launch.tip.experimental"))
            if tip.missing_tool:
                sub.append(t("gui.launch.tip.missing", tool=tip.missing_tool))
            if tip.token.startswith("arg:"):
                sub.append(t("gui.launch.tip.arg"))
            parsed = tip.as_parsed()
            already = current is not None and merge(current, parsed) == current
            row = Adw.SwitchRow(title=tip.text, subtitle=" · ".join(sub))
            row.set_use_markup(False)
            usable = not tip.missing_tool and not already
            row.set_sensitive(usable)
            if already:
                row.set_subtitle(t("gui.launch.tip.already"))
            on = (usable and tip.share >= PRESELECT_SHARE and not tip.token.startswith("arg:")
                  and fits and not tip.experimental)
            if tip.token in PERF_WRAPPERS:
                on, perf_on = on and not perf_on, perf_on or on
            row.set_active(on)
            row.connect("notify::active", self._update)
            self.tips_group.add(row)
            self.tips.append((row, parsed))

    # ----- строка -----
    def _switch(self, field: str) -> Adw.SwitchRow:
        row = Adw.SwitchRow()
        row.set_use_markup(False)  # в подписях есть <appid> и %command% — разметку выключаем до текста
        row.set_title(t(f"gui.launch.{field}"))
        row.set_subtitle(t(f"gui.launch.{field}.sub"))
        row.connect("notify::active", self._update)
        self.switches[field] = row
        return row

    def _compose(self) -> str | None:
        """Итоговая строка: переключатели + оставленное из Steam + выбранные советы."""
        text = build(self.cfg)
        if self.current is None:
            return text
        own = parse(text)
        if own is None:
            return None
        result = Parsed()
        for row, p in self.kept:
            if row.get_active():
                result = merge(result, p)
        result = merge(result, own)
        for row, p in self.tips:
            if row.get_active() and row.get_sensitive():
                result = merge(result, p)
        return compose(result)

    def _update(self, *_):
        if self.loading:
            return
        for field, row in self.switches.items():
            setattr(self.cfg, field, row.get_active())
        self.gs_expander.set_sensitive(self.cfg.gamescope)
        self.cfg.gamescope_width = int(self.gs_width.get_value())
        self.cfg.gamescope_height = int(self.gs_height.get_value())
        self.cfg.gamescope_fullscreen = self.gs_full.get_active()
        self.cfg.cpu_cores = int(self.cores.get_value())
        self.cfg.game_args = self.args.get_text()
        problems = []
        try:
            text = self._compose()
        except ValueError:
            text = None
            problems.append(t("gui.launch.bad_quotes"))
        s = self.current
        if s is not None and not self.base_ok:
            problems.append(t("gui.launch.complex"))
        if text is not None:
            self.result.set_text(text)
            problems += [hint for _, hint in analyze_launch_options(text)]
        elif not problems:
            problems.append(t("gui.launch.args_complex"))
        can_write = s is not None and s.config is not None and self.base_ok and text is not None
        self.write_btn.set_visible(s is not None)
        self.write_btn.set_sensitive(can_write and text.strip() != (s.options or "%command%").strip())
        last = steamcfg.last_change(s.game.appid) if s is not None else None
        self.undo_btn.set_visible(bool(last) and not last.get("undo") and last.get("new") == (s.options or None))
        self.warnings.set_text("\n".join(problems))
        self.warnings.set_visible(bool(problems))

    # ----- запись в Steam -----
    def _write(self):
        s = self.current
        text = self.result.get_text()
        value = None if text.strip() == "%command%" else text
        self._apply(s, value, undo=False)

    def _undo(self):
        s = self.current
        last = steamcfg.last_change(s.game.appid)
        if last:
            self._apply(s, last.get("old"), undo=True)

    def _apply(self, s: SteamSettings, value: str | None, undo: bool):
        try:
            steamcfg.write(s.config, s.game.appid, value, undo=undo)
        except steamcfg.SteamConfigError as e:
            msg = t("gui.launch.steam_running") if str(e) == "steam_running" else t("gui.launch.write_failed", error=e)
            self.warnings.set_text(msg)
            self.warnings.set_visible(True)
            return
        s.options = value or ""
        self.toast(t("gui.launch.undone") if undo else t("gui.launch.written", name=s.game.name))
        self._on_game()
