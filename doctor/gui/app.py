"""Графическое окно на GTK4 + libadwaita.

Окно — только «лицо»: оно запускает те же проверки (doctor.runner) в фоновом потоке
и показывает результат. Установка идёт через pkexec и только после нажатия «Установить».
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from doctor import __version__, fixer, i18n  # noqa: E402
from doctor.checks import ALL_GROUPS  # noqa: E402
from doctor.gui import style  # noqa: E402
from doctor.i18n import t  # noqa: E402
from doctor.models import CheckResult, Context, Status  # noqa: E402
from doctor.runner import run_all, summarize  # noqa: E402

APP_ID = "io.github.lgdoctor.LinuxGamerDoctor"
SETTINGS = Path(GLib.get_user_config_dir()) / "linux-gamer-doctor" / "gui.json"

STATUS_ICON = {
    Status.OK: "object-select-symbolic",
    Status.WARN: "dialog-warning-symbolic",
    Status.FAIL: "dialog-error-symbolic",
    Status.UNKNOWN: "dialog-question-symbolic",
}
SEVERITY = [Status.FAIL, Status.WARN, Status.UNKNOWN, Status.OK]  # порядок важности
GROUP_ICON = {
    "distro": "computer-symbolic",
    "gpu": "video-display-symbolic",
    "vulkan": "applications-graphics-symbolic",
    "multilib": "package-x-generic-symbolic",
    "steam": "applications-games-symbolic",
    "disks": "drive-harddisk-symbolic",
    "proton": "system-run-symbolic",
    "tools": "applications-utilities-symbolic",
    "tuning": "preferences-system-symbolic",
    "games": "input-gaming-symbolic",
}
URL = re.compile(r"https?://[^\s)»]+")


# ---------------- настройки окна ----------------

def load_settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text())
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps(data))
    except OSError:
        pass  # не смогли запомнить язык — не повод мешать работе


# ---------------- мелкие виджеты ----------------

def icon(name: str, fallback: str = "dialog-information-symbolic") -> Gtk.Image:
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    return Gtk.Image.new_from_icon_name(name if theme.has_icon(name) else fallback)


def status_chip(status: Status) -> Gtk.Widget:
    img = icon(STATUS_ICON[status])
    img.add_css_class("chip")
    img.add_css_class(status.value)
    img.set_valign(Gtk.Align.CENTER)
    img.set_tooltip_text(t(f"status.{status.value}"))
    return img


def label(text: str, *classes: str, wrap: bool = True, selectable: bool = False,
          markup: bool = False) -> Gtk.Label:
    lab = Gtk.Label(xalign=0, wrap=wrap, selectable=selectable)
    lab.set_wrap_mode(2)  # Pango.WrapMode.WORD_CHAR — длинные пути не ломают вёрстку
    if markup:
        lab.set_markup(text)
    else:
        lab.set_text(text)
    for c in classes:
        lab.add_css_class(c)
    return lab


def linkify(text: str) -> str:
    """Экранирует текст для Pango и делает ссылки кликабельными."""
    out, pos = [], 0
    for m in URL.finditer(text):
        out.append(GLib.markup_escape_text(text[pos:m.start()]))
        url = GLib.markup_escape_text(m.group(0))
        out.append(f'<a href="{url}">{url}</a>')
        pos = m.end()
    out.append(GLib.markup_escape_text(text[pos:]))
    return "".join(out)


def copy_to_clipboard(widget: Gtk.Widget, text: str) -> None:
    provider = Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8",
                                                 GLib.Bytes.new(text.encode()))
    widget.get_clipboard().set_content(provider)


def worst(results: list[CheckResult]) -> Status:
    return min((r.status for r in results), key=SEVERITY.index, default=Status.OK)


# ---------------- окно ----------------

class DoctorWindow(Adw.ApplicationWindow):
    def __init__(self, app: "DoctorApp"):
        super().__init__(application=app, title=t("app.title"))
        self.app = app
        self.set_default_size(1120, 780)
        self.set_size_request(360, 480)
        self.results: list[CheckResult] = []
        self.ctx: Context | None = None
        self.plan: fixer.Plan | None = None
        self.rows: dict[str, Adw.PreferencesRow] = {}  # id проверки -> строка (для перехода из обзора)

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(230)
        self.split.set_max_sidebar_width(300)
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 720sp"))
        bp.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(bp)

        self._build_sidebar()
        self._build_content()
        self.refresh()

    # ----- каркас -----
    def _build_sidebar(self):
        header = Adw.HeaderBar()
        menu = Gio.Menu()
        lang_menu = Gio.Menu()
        for code, name in (("ru", "Русский"), ("en", "English")):
            item = Gio.MenuItem.new(name, None)
            item.set_action_and_target_value("app.language", GLib.Variant.new_string(code))
            lang_menu.append_item(item)
        menu.append_submenu(t("gui.menu.language"), lang_menu)
        menu.append(t("gui.menu.about"), "app.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                  tooltip_text=t("gui.menu"))
        header.pack_end(menu_btn)

        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.add_css_class("navigation-sidebar")
        self.nav.connect("row-selected", self._on_nav_selected)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scroller.set_child(self.nav)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(scroller)
        self.split.set_sidebar(Adw.NavigationPage.new(view, t("app.title")))

    def _build_content(self):
        self.header = Adw.HeaderBar()
        self.title = Adw.WindowTitle(title=t("gui.overview"), subtitle="")
        self.header.set_title_widget(self.title)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=t("gui.refresh"))
        refresh.connect("clicked", lambda *_: self.refresh())
        self.header.pack_start(refresh)
        self.fix_btn = Gtk.Button(label=t("gui.fix.button"), visible=False)
        self.fix_btn.add_css_class("suggested-action")
        self.fix_btn.connect("clicked", lambda *_: self.open_fix_dialog())
        self.header.pack_end(self.fix_btn)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        view = Adw.ToolbarView()
        view.add_top_bar(self.header)
        view.set_content(self.stack)
        self.content_page = Adw.NavigationPage.new(view, t("gui.overview"))
        self.split.set_content(self.content_page)

    # ----- проверка -----
    def refresh(self):
        self._show_loading()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            ctx = Context()
            results = run_all(ALL_GROUPS, ctx)
            if os.environ.get("DOCTOR_GUI_DEMO"):
                from doctor.gui.demo import add_demo_problems
                results, ctx = add_demo_problems(results, ctx)
            plan = fixer.build_plan(results, ctx)
            GLib.idle_add(self._on_results, results, ctx, plan)
        except Exception as e:  # noqa: BLE001 — показываем ошибку в окне, а не молча
            GLib.idle_add(self._show_crash, f"{type(e).__name__}: {e}")

    def _show_loading(self):
        spinner = Adw.Spinner()
        spinner.set_size_request(48, 48)
        page = Adw.StatusPage(title=t("gui.loading"), description=t("gui.loading_sub"), child=spinner)
        self._set_page(page, "loading")
        self.fix_btn.set_visible(False)

    def _show_crash(self, error: str):
        page = Adw.StatusPage(icon_name="dialog-error-symbolic", title=t("gui.crashed", error=""),
                              description=GLib.markup_escape_text(error))
        self._set_page(page, "crash")

    def _set_page(self, widget: Gtk.Widget, name: str):
        old = self.stack.get_child_by_name(name)
        if old is not None:
            self.stack.remove(old)
        self.stack.add_named(widget, name)
        self.stack.set_visible_child_name(name)

    def _on_results(self, results, ctx, plan):
        self.results, self.ctx, self.plan = results, ctx, plan
        for child in list(self.stack):
            self.stack.remove(child)
        self.rows.clear()
        self.groups = list(dict.fromkeys(r.group for r in results))
        self.stack.add_named(self._overview_page(), "overview")
        for g in self.groups:
            self.stack.add_named(self._group_page(g), f"group:{g}")
        self._fill_sidebar()
        self.fix_btn.set_visible(bool(plan.steps))
        self.title.set_subtitle(self._system_line())
        GLib.idle_add(self._maybe_snapshot)
        return False

    def _system_line(self) -> str:
        by_id = {r.id: r.value for r in self.results}
        parts = [by_id.get("distro.os", ""), by_id.get("distro.kernel", "")]
        return " · ".join(p for p in parts if p)

    # ----- боковая панель -----
    def _fill_sidebar(self):
        self.nav.remove_all()
        self._nav_names = ["overview"] + [f"group:{g}" for g in self.groups]
        self.nav.append(self._nav_row("view-grid-symbolic", t("gui.overview"), None))
        for g in self.groups:
            items = [r for r in self.results if r.group == g]
            self.nav.append(self._nav_row(GROUP_ICON.get(g, "folder-symbolic"), t(f"group.{g}"), items))
        self.nav.select_row(self.nav.get_row_at_index(0))

    def _nav_row(self, icon_name: str, text: str, items: list[CheckResult] | None) -> Gtk.ListBoxRow:
        box = Gtk.Box(spacing=12, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        box.append(icon(icon_name, "folder-symbolic"))
        box.append(label(text, wrap=False))
        spacer = Gtk.Box(hexpand=True)
        box.append(spacer)
        if items:
            st = worst(items)
            problems = sum(1 for r in items if r.status in (Status.FAIL, Status.WARN))
            if problems:
                box.append(label(str(problems), "sidebar-count", wrap=False))
            dot = Gtk.Box(valign=Gtk.Align.CENTER)
            dot.add_css_class("dot")
            dot.add_css_class(st.value)
            dot.set_tooltip_text(t(f"status.{st.value}"))
            box.append(dot)
        row = Gtk.ListBoxRow()
        row.set_child(box)
        return row

    def _on_nav_selected(self, _box, row):
        if row is None:
            return
        name = self._nav_names[row.get_index()]
        self.stack.set_visible_child_name(name)
        title = t("gui.overview") if name == "overview" else t(f"group.{name.split(':', 1)[1]}")
        self.title.set_title(title)
        self.content_page.set_title(title)
        self.split.set_show_content(True)

    def go_to_check(self, result: CheckResult):
        idx = self.groups.index(result.group) + 1
        self.nav.select_row(self.nav.get_row_at_index(idx))
        row = self.rows.get(result.id + "#" + result.title)
        if row is not None:
            if isinstance(row, Adw.ExpanderRow):
                row.set_expanded(True)
            GLib.idle_add(row.grab_focus)

    # ----- обзор -----
    def _overview_page(self) -> Gtk.Widget:
        s = summarize(self.results)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                      margin_top=24, margin_bottom=32, margin_start=18, margin_end=18)

        # главная карточка
        state = "fail" if s["fail"] else "warn" if s["warn"] else "ok"
        hero = Gtk.Box(spacing=20)
        hero.add_css_class("hero")
        hero.add_css_class(state)
        big = icon(STATUS_ICON[Status(state)])
        big.set_pixel_size(36)
        big.add_css_class("hero-icon")
        big.add_css_class("chip")
        big.add_css_class(state)
        big.set_valign(Gtk.Align.CENTER)
        hero.append(big)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        text.append(label(t(f"gui.hero.{state}"), "hero-title"))
        text.append(label(t("gui.hero.sub_fail") if s["fail"] else t("gui.hero.sub_ok"), "hero-sub"))
        sysline = self._system_line()
        gpu = next((r.value for r in self.results if r.id == "gpu.detect"), "")
        text.append(label(" · ".join(p for p in (sysline, gpu) if p), "muted", "caption"))
        hero.append(text)
        box.append(hero)

        # счётчики
        stats = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                            max_children_per_line=4, min_children_per_line=2,
                            column_spacing=12, row_spacing=12)
        for st in (Status.OK, Status.WARN, Status.FAIL, Status.UNKNOWN):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            card.add_css_class("stat")
            card.add_css_class(st.value)
            card.append(label(str(s[st.value]), "stat-number", wrap=False))
            card.append(label(t(f"gui.stat.{st.value}"), "stat-label", wrap=False))
            stats.append(card)
        box.append(stats)

        # баннер автоисправления
        if self.plan and self.plan.steps:
            count = sum(len(st.packages) for st in self.plan.steps)
            banner = Gtk.Box(spacing=12)
            banner.add_css_class("fix-banner")
            banner.append(icon("software-update-available-symbolic", "system-software-install-symbolic"))
            banner.append(self._expand(label(t("gui.fix.banner", count=count))))
            btn = Gtk.Button(label=t("gui.fix.button"), valign=Gtk.Align.CENTER)
            btn.add_css_class("suggested-action")
            btn.add_css_class("pill")
            btn.connect("clicked", lambda *_: self.open_fix_dialog())
            banner.append(btn)
            box.append(banner)

        # что сделать
        todo = Adw.PreferencesGroup(title=t("gui.todo.title"), description=t("gui.todo.desc"))
        problems = sorted((r for r in self.results if r.status != Status.OK),
                          key=lambda r: SEVERITY.index(r.status))
        if not problems:
            row = Adw.ActionRow(title=t("gui.todo.empty"))
            row.add_prefix(status_chip(Status.OK))
            todo.add(row)
        for r in problems:
            row = Adw.ActionRow(title=r.title, subtitle=t(f"group.{r.group}"), activatable=True)
            row.set_use_markup(False)
            row.add_prefix(status_chip(r.status))
            row.add_suffix(icon("go-next-symbolic"))
            row.connect("activated", lambda _row, res=r: self.go_to_check(res))
            todo.add(row)
        box.append(todo)

        clamp = Adw.Clamp(maximum_size=920, child=box)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(clamp)
        return scroller

    @staticmethod
    def _expand(widget: Gtk.Widget) -> Gtk.Widget:
        widget.set_hexpand(True)
        widget.set_valign(Gtk.Align.CENTER)
        return widget

    # ----- страница группы -----
    def _group_page(self, group: str) -> Gtk.Widget:
        items = [r for r in self.results if r.group == group]
        s = summarize(items)
        page = Adw.PreferencesPage()
        pg = Adw.PreferencesGroup(title=t(f"group.{group}"), description=t("gui.group.desc", **s))
        for r in items:
            row = self._result_row(r)
            self.rows[r.id + "#" + r.title] = row
            pg.add(row)
        page.add(pg)
        return page

    def _result_row(self, r: CheckResult) -> Adw.PreferencesRow:
        value_lines = (r.value or "—").split("\n")
        has_details = bool(r.hint or r.fix or r.error or len(value_lines) > 1)
        if not has_details:
            row = Adw.ActionRow(title=r.title, subtitle=value_lines[0])
            row.set_use_markup(False)
            row.set_subtitle_selectable(True)
            row.add_prefix(status_chip(r.status))
            return row

        row = Adw.ExpanderRow(title=r.title, subtitle=value_lines[0])
        row.set_use_markup(False)
        row.set_subtitle_lines(2)
        row.add_prefix(status_chip(r.status))
        row.set_expanded(r.status in (Status.FAIL, Status.WARN))

        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        detail.add_css_class("detail")
        if len(value_lines) > 1:
            detail.append(label(linkify("\n".join(value_lines[1:])), "muted", selectable=True, markup=True))
        if r.hint:
            detail.append(label(linkify(r.hint), selectable=True, markup=True))
        if r.fix:
            detail.append(label(t("gui.details.fix").upper(), "detail-title"))
            line = Gtk.Box(spacing=8)
            code = label(r.fix, "code", selectable=True)
            code.set_hexpand(True)
            line.append(code)
            copy = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text=t("gui.copy"),
                              valign=Gtk.Align.CENTER)
            copy.add_css_class("flat")
            copy.connect("clicked", lambda *_: self._copy(r.fix))
            line.append(copy)
            detail.append(line)
        if r.error:
            detail.append(label(t("gui.details.error").upper(), "detail-title"))
            detail.append(label(r.error, "error-box", selectable=True))
        holder = Gtk.ListBoxRow(activatable=False, selectable=False)
        holder.set_child(detail)
        row.add_row(holder)
        return row

    def _copy(self, text: str):
        copy_to_clipboard(self, text)
        self.toasts.add_toast(Adw.Toast.new(t("gui.copied")))

    # ----- исправление -----
    def open_fix_dialog(self):
        if not self.plan or not self.plan.steps:
            return
        FixDialog(self).present(self)

    # ----- снимок экрана для разработчиков (DOCTOR_GUI_SNAPSHOT=путь.png) -----
    def _maybe_snapshot(self):
        path = os.environ.get("DOCTOR_GUI_SNAPSHOT")
        if not path:
            return False
        page = os.environ.get("DOCTOR_GUI_PAGE", "overview")
        if page != "overview" and page in self.groups:
            self.nav.select_row(self.nav.get_row_at_index(self.groups.index(page) + 1))
        if os.environ.get("DOCTOR_GUI_OPEN_FIX"):
            self.open_fix_dialog()
        GLib.timeout_add(900, self._save_snapshot, path)
        return False

    def _save_snapshot(self, path: str):
        paintable = Gtk.WidgetPaintable.new(self)
        w, h = self.get_width(), self.get_height()
        snap = Gtk.Snapshot()
        paintable.snapshot(snap, w, h)
        node = snap.to_node()
        if node is not None:
            texture = self.get_renderer().render_texture(node, None)
            texture.save_to_png(path)
        self.app.quit()
        return False


class FixDialog(Adw.Dialog):
    def __init__(self, win: DoctorWindow):
        super().__init__(title=t("gui.fix.title"), content_width=640)
        self.win = win
        self.pm = win.ctx.package_manager if win.ctx else None
        self.commands = [fixer.gui_argv(step, self.pm) for step in win.plan.steps]

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                      margin_top=12, margin_bottom=18, margin_start=18, margin_end=18)
        box.append(label(t("gui.fix.intro")))
        for step, argv in zip(win.plan.steps, self.commands):
            box.append(label(t(f"fix.kind.{step.kind}").upper(), "detail-title"))
            box.append(label(" ".join(argv), "code", selectable=True))
        if win.plan.skipped:
            box.append(label(t("gui.fix.skipped", packages=", ".join(win.plan.skipped)), "error-box"))

        self.status = label("", "muted")
        box.append(self.status)
        self.log = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                vexpand=True)
        self.log.add_css_class("log")
        self.log_scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=180, visible=False)
        self.log_scroll.set_child(self.log)
        box.append(self.log_scroll)

        buttons = Gtk.Box(spacing=10, halign=Gtk.Align.END)
        copy = Gtk.Button(label=t("gui.fix.copy"))
        copy.add_css_class("pill")
        copy.connect("clicked", lambda *_: win._copy("\n".join(s.command for s in win.plan.steps)))
        buttons.append(copy)
        self.install = Gtk.Button(label=t("gui.fix.install"))
        self.install.add_css_class("pill")
        self.install.add_css_class("suggested-action")
        self.install.connect("clicked", self._on_install)
        if not GLib.find_program_in_path("pkexec"):
            self.install.set_sensitive(False)
            self.status.set_text(t("gui.fix.no_pkexec"))
        buttons.append(self.install)
        box.append(buttons)

        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True)
        scroller.set_child(box)
        view.set_content(scroller)
        self.set_child(view)
        # иначе фокус попадает на выделяемую команду и она вся подсвечивается
        self.set_focus(self.install if self.install.get_sensitive() else copy)

    def _append(self, text: str):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), text)
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)
        return False

    def _on_install(self, *_):
        self.install.set_sensitive(False)
        self.log_scroll.set_visible(True)
        self.status.set_text(t("gui.fix.running"))
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        for argv in self.commands:
            GLib.idle_add(self._append, "$ " + " ".join(argv) + "\n")
            try:
                proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    GLib.idle_add(self._append, line)
                code = proc.wait()
            except OSError as e:
                GLib.idle_add(self._append, f"{e}\n")
                code = -1
            if code != 0:
                GLib.idle_add(self._finish, False, code)
                return
        GLib.idle_add(self._finish, True, 0)

    def _finish(self, ok: bool, code: int):
        if ok:
            self.win.toasts.add_toast(Adw.Toast.new(t("gui.fix.done")))
            self.close()
            self.win.refresh()
        else:
            self.status.set_text(t("gui.fix.failed", code=code))
            self.install.set_sensitive(True)
        return False


class DoctorApp(Adw.Application):
    def __init__(self, lang: str | None = None):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.settings = load_settings()
        self.lang = lang or self.settings.get("lang") or i18n.DEFAULT
        i18n.set_language(self.lang)
        self.win: DoctorWindow | None = None
        self.connect("activate", self._on_activate)

    def _on_activate(self, *_):
        if os.environ.get("DOCTOR_GUI_SNAPSHOT"):
            # на невидимом дисплее (Broadway) кадры анимаций не идут — снимок застал бы их начало
            Gtk.Settings.get_default().set_property("gtk-enable-animations", False)
        self._setup_style()
        lang_action = Gio.SimpleAction.new_stateful("language", GLib.VariantType.new("s"),
                                                    GLib.Variant.new_string(self.lang))
        lang_action.connect("change-state", self._on_language)
        self.add_action(lang_action)
        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", self._on_about)
        self.add_action(about)
        self.win = DoctorWindow(self)
        self.win.present()

    def _setup_style(self):
        manager = Adw.StyleManager.get_default()
        scheme = os.environ.get("DOCTOR_GUI_SCHEME")  # light | dark — для снимков экрана
        if scheme in ("light", "dark"):
            manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if scheme == "light"
                                     else Adw.ColorScheme.FORCE_DARK)
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), self.provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        apply = lambda *_: self.provider.load_from_string(  # noqa: E731
            style.css(style.DARK if manager.get_dark() else style.LIGHT))
        manager.connect("notify::dark", apply)
        apply()

    def _on_language(self, action, value):
        code = value.get_string()
        if code == self.lang:
            return
        action.set_state(value)
        self.lang = code
        i18n.set_language(code)
        self.settings["lang"] = code
        save_settings(self.settings)
        # Тексты собираются при проверке, поэтому окно пересоздаём целиком.
        old = self.win
        self.win = DoctorWindow(self)
        self.win.present()
        old.destroy()

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(application_name=t("app.title"), version=__version__,
                                 comments=t("gui.about.comments"),
                                 application_icon="input-gaming-symbolic",
                                 license_type=Gtk.License.GPL_3_0)
        dialog.present(self.win)


def run(lang: str | None = None) -> int:
    return DoctorApp(lang).run([])
