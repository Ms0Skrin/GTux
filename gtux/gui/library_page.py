"""Страница «Библиотека»: все игры Steam, включая неустановленные, с итогом под этот ПК.
Установленную игру можно открыть на странице «Параметры запуска»."""

from __future__ import annotations

from gi.repository import Adw, Gtk

from gtux import library
from gtux.i18n import t
from gtux.models import Status

STATUS_ICON = {
    Status.OK: "object-select-symbolic",
    Status.WARN: "dialog-warning-symbolic",
    Status.FAIL: "dialog-error-symbolic",
    Status.UNKNOWN: "dialog-question-symbolic",
}
FILTERS = ["all", "installed", "problems"]


class LibraryPage(Adw.PreferencesPage):
    def __init__(self, games: list[library.LibraryGame], open_game=None):
        super().__init__()
        self.open_game = open_game or (lambda appid: None)
        self.rows: list[tuple[Adw.ActionRow, library.LibraryGame, Status]] = []

        top = Adw.PreferencesGroup(description=t("gui.library.desc"))
        bar = Gtk.Box(spacing=8)
        self.search = Gtk.SearchEntry(placeholder_text=t("gui.library.search"), hexpand=True)
        self.search.connect("search-changed", lambda *_: self._filter())
        bar.append(self.search)
        self.kind = Gtk.DropDown.new_from_strings([t(f"gui.library.filter.{f}") for f in FILTERS])
        self.kind.connect("notify::selected", lambda *_: self._filter())
        bar.append(self.kind)
        top.add(bar)
        self.add(top)

        self.group = Adw.PreferencesGroup()
        if not games:
            self.group.add(Adw.ActionRow(title=t("gui.library.empty")))
        for game in games:
            status, parts = library.summary(game)
            row = Adw.ActionRow()
            row.set_use_markup(False)  # в названиях игр бывают & и < — разметку выключаем до текста
            row.set_title(game.name)
            row.set_subtitle(" · ".join(parts))
            img = Gtk.Image.new_from_icon_name(STATUS_ICON[status])
            img.add_css_class(f"status-{status.value}")
            row.add_prefix(img)
            if game.installed:
                row.set_activatable(True)
                row.set_tooltip_text(t("gui.library.open"))
                row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
                row.connect("activated", lambda _r, appid=game.appid: self.open_game(appid))
            else:
                link = Gtk.LinkButton(uri=f"https://www.protondb.com/app/{game.appid}", label="ProtonDB",
                                      valign=Gtk.Align.CENTER)
                row.add_suffix(link)
            self.group.add(row)
            self.rows.append((row, game, status))
        self.add(self.group)
        self._filter()

    def _filter(self):
        text = self.search.get_text().strip().lower()
        kind = FILTERS[self.kind.get_selected()] if self.kind.get_selected() < len(FILTERS) else "all"
        shown = 0
        for row, game, status in self.rows:
            visible = (not text or text in game.name.lower()) and (
                kind == "all" or (kind == "installed" and game.installed)
                or (kind == "problems" and status in (Status.FAIL, Status.WARN)))
            row.set_visible(visible)
            shown += visible
        self.group.set_title(t("gui.library.count", shown=shown, total=len(self.rows)) if self.rows else "")
