"""Диалог установки в терминале: показать план, спросить, выполнить."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markup import escape
from rich.text import Text

from gtux import fixer
from gtux.i18n import t
from gtux.models import CheckResult, Context, Status

YES = {"y", "yes", "д", "да"}
SELECT = {"s", "select", "в", "выбрать"}


def _ask(console: Console, prompt: str) -> str:
    try:
        return console.input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return ""


def _show_plan(console: Console, plan: fixer.Plan) -> None:
    console.print(f"\n[bold]{escape(t('fix.plan_title'))}[/]")
    for i, step in enumerate(plan.steps, 1):
        what = t("fix.kind." + step.kind) + (f" ({step.title})" if step.title else "")
        console.print(f"  {i}. {escape(what)}")
        console.print(f"     [cyan]{escape(step.command)}[/]")
    if plan.skipped:
        console.print(f"\n[yellow]{escape(t(plan.skipped_reason, packages=', '.join(plan.skipped)))}[/]")
    if plan.unavailable:
        console.print(f"\n[yellow]{escape(t(plan.unavailable_hint, packages=', '.join(plan.unavailable)))}[/]")
    if plan.offers:
        console.print(f"\n[bold]{escape(t('fix.offers_title'))}[/]")
        for step in plan.offers:
            console.print(f"  • {escape(_what(step))}")
            for warning in dict.fromkeys(st.warning for st in step.chain() if st.warning):
                console.print(f"     [yellow]{escape(t(warning))}[/]")
            console.print(f"     [cyan]{escape(' && '.join(s.command for s in step.chain()))}[/]")


def _what(step: fixer.Step) -> str:
    return t("fix.kind." + step.kind) + (f" ({step.title})" if step.title else "")


def _show_recheck(console: Console, before: list[CheckResult], after: list[CheckResult]) -> None:
    """Повторная проверка: что стало лучше, а что осталось."""
    old = {r.id: r.status for r in before}
    for r in after:
        if r.id in old and old[r.id] != r.status:
            style = "green" if r.status == Status.OK else "yellow"
            console.print(Text("  • " + t("history.status", title=r.title, old=t(f"status.{old[r.id].value}"),
                                          new=t(f"status.{r.status.value}")), style=style))
    if any(r.id == "gpu.nvidia_version" and r.status == Status.FAIL for r in after):
        console.print(f"[yellow]{escape(t('fix.reboot'))}[/]")


def run(results: list[CheckResult], ctx: Context, console: Console | None = None,
        recheck=None) -> int:
    """recheck() — заново запустить проверки после исправления (необязательно)."""
    console = console or Console()
    plan = fixer.build_plan(results, ctx)
    if not plan.steps and not plan.skipped and not plan.offers and not plan.unavailable:
        console.print(f"\n[green]{escape(t('fix.nothing'))}[/]")
        return 0
    if not plan.steps:
        console.print(f"\n[green]{escape(t('fix.nothing'))}[/]")
    _show_plan(console, plan)
    if not plan.steps and not plan.offers:
        return 0
    if not sys.stdin.isatty():
        console.print(f"\n[yellow]{escape(t('fix.not_tty'))}[/]")
        return 0

    answer = _ask(console, "\n" + t("fix.confirm"))
    if answer in SELECT:
        chosen = [p for p in fixer.wanted_packages(results)
                  if p not in plan.skipped and _ask(console, t("fix.ask_package", package=p)) in YES]
        actions = [s for s in plan.steps if s.kind not in fixer.PACKAGE_KINDS
                   and _ask(console, t("fix.ask_step", what=t("fix.kind." + s.kind), title=s.title)) in YES]
        offers = [s for s in plan.offers if _ask(console, t("fix.ask_offer", what=t("fix.kind." + s.kind),
                                                              title=s.title)) in YES]
        plan = fixer.build_plan(results, ctx, only=chosen)
        plan.steps = [s for s in plan.steps if s.kind in fixer.PACKAGE_KINDS] + actions + offers
        plan.offers = []
        if not plan.steps:
            console.print(t("fix.cancelled"))
            return 0
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
        if recheck is not None:
            _show_recheck(console, results, recheck())
        return 0
    console.print(f"\n[bold red]{escape(t('fix.failed', command=failed.command, code=code))}[/]")
    return 1
