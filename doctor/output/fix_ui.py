"""Диалог установки в терминале: показать план, спросить, выполнить."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markup import escape

from doctor import fixer
from doctor.i18n import t
from doctor.models import CheckResult, Context

YES = {"y", "yes", "д", "да"}
SELECT = {"s", "в", "выбрать"}


def _ask(console: Console, prompt: str) -> str:
    try:
        return console.input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return ""


def _show_plan(console: Console, plan: fixer.Plan) -> None:
    console.print(f"\n[bold]{escape(t('fix.plan_title'))}[/]")
    for i, step in enumerate(plan.steps, 1):
        console.print(f"  {i}. {escape(t('fix.kind.' + step.kind))}")
        console.print(f"     [cyan]{escape(step.command)}[/]")
    if plan.skipped:
        console.print(f"\n[yellow]{escape(t(plan.skipped_reason, packages=', '.join(plan.skipped)))}[/]")


def run(results: list[CheckResult], ctx: Context, console: Console | None = None) -> int:
    console = console or Console()
    plan = fixer.build_plan(results, ctx)
    if not plan.steps and not plan.skipped:
        console.print(f"\n[green]{escape(t('fix.nothing'))}[/]")
        return 0
    _show_plan(console, plan)
    if not plan.steps:
        return 0
    if not sys.stdin.isatty():
        console.print(f"\n[yellow]{escape(t('fix.not_tty'))}[/]")
        return 0

    answer = _ask(console, "\n" + t("fix.confirm"))
    if answer in SELECT:
        chosen = [p for p in fixer.wanted_packages(results)
                  if p not in plan.skipped and _ask(console, t("fix.ask_package", package=p)) in YES]
        if not chosen:
            console.print(t("fix.cancelled"))
            return 0
        plan = fixer.build_plan(results, ctx, only=chosen)
        _show_plan(console, plan)
        answer = _ask(console, "\n" + t("fix.confirm_short"))
    if answer not in YES:
        console.print(t("fix.cancelled"))
        return 0

    def echo(step, error=None):
        if step is not None:
            console.print(f"\n[bold]→[/] [cyan]{escape(step.command)}[/]")
        if error:
            console.print(f"[red]{escape(error)}[/]")

    ok, failed, code = fixer.execute(plan, echo)
    if ok:
        console.print(f"\n[bold green]{escape(t('fix.done'))}[/]")
        return 0
    console.print(f"\n[bold red]{escape(t('fix.failed', command=failed.command, code=code))}[/]")
    return 1
