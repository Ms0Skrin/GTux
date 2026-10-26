"""Красивый вывод в терминал через rich."""

from __future__ import annotations

import time

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from doctor.i18n import t
from doctor.models import CheckResult, Status
from doctor.runner import summarize

STYLES = {
    Status.OK: "bold green",
    Status.WARN: "bold yellow",
    Status.FAIL: "bold red",
    Status.UNKNOWN: "bold bright_black",
}


def _result_cell(r: CheckResult) -> Text:
    cell = Text(r.value or "—")
    if r.status != Status.OK:
        if r.hint:
            cell.append("\n" + r.hint, style="dim")
        if r.fix:
            cell.append("\n" + t("ui.fix"), style="dim")
            cell.append(r.fix, style="cyan")
    if r.error:
        cell.append("\n" + t("ui.error") + r.error, style="red dim")
    return cell


def render_changes(console: Console, changes, previous_time: float | None) -> None:
    if not changes:
        return
    when = time.strftime("%d.%m %H:%M", time.localtime(previous_time)) if previous_time else "?"
    console.print(f"\n[bold]{escape(t('history.title', when=when))}[/]")
    for c in changes:
        style = STYLES.get(c.new_status, "") if c.new_status else "dim"
        if c.kind == "status":
            text = t("history.status", title=c.title, old=t(f"status.{c.old}"), new=t(f"status.{c.new}"))
        elif c.kind == "value":
            text = t("history.value", title=c.title, old=c.old, new=c.new)
        else:
            text = t(f"history.{c.kind}", title=c.title)
        console.print(Text("  • " + text, style=style))


def render(results: list[CheckResult], console: Console | None = None,
           show_fix_hint: bool = True, changes=None, previous_time: float | None = None) -> None:
    console = console or Console()
    console.print(f"[bold]{escape(t('app.title'))}[/]  [dim]{escape(t('app.subtitle'))}[/]\n")

    table = Table(show_lines=False, expand=True)
    table.add_column(t("ui.col.status"), no_wrap=True)
    table.add_column(t("ui.col.check"), style="bold")
    table.add_column(t("ui.col.result"), ratio=1)

    group = None
    for r in results:
        if r.group != group:
            if group is not None:
                table.add_section()
            group = r.group
            table.add_row("", Text(t(f"group.{group}"), style="bold magenta"), "")
        table.add_row(Text(t(f"status.{r.status.value}"), style=STYLES[r.status]),
                      r.title, _result_cell(r))
    console.print(table)
    render_changes(console, changes or [], previous_time)

    s = summarize(results)
    summary = Text()
    summary.append(t("ui.summary", **s))
    console.print(summary)
    if s["fail"]:
        console.print(t("ui.has_problems"), style="bold red")
    else:
        console.print(t("ui.all_good"), style="bold green")
    console.print(t("ui.note"), style="dim")
    if show_fix_hint and any(r.packages and r.status != Status.OK for r in results):
        console.print(t("ui.fix_hint"), style="bold cyan")
