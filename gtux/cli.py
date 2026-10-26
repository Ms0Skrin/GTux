"""Командная строка: gtux [--gui | --fix | --json | --report] [--lang ru|en] [--debug]

Copyright (C) 2026 Евгений
SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import logging
import sys
from pathlib import Path

from gtux import __version__, i18n
from gtux import log as gtux_log
from gtux.i18n import t

log = logging.getLogger("gtux.main")


def main() -> int:
    parser = argparse.ArgumentParser(prog="gtux", description=t("cli.description"),
                                     epilog=t("cli.log_epilog", path=gtux_log.log_path()))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help=t("cli.gui"))
    mode.add_argument("--fix", action="store_true", help=t("cli.fix"))
    mode.add_argument("--json", action="store_true", help=t("cli.json"))
    mode.add_argument("--report", action="store_true", help=t("cli.report"))
    mode.add_argument("--update-kb", action="store_true", help=t("cli.update_kb"))
    mode.add_argument("--install-ge", metavar="DIR", help=t("cli.install_ge"))
    mode.add_argument("--library", action="store_true", help=t("cli.library"))
    parser.add_argument("--lang", choices=i18n.AVAILABLE, default=None, help=t("cli.lang"))
    parser.add_argument("--debug", action="store_true", help=t("cli.debug"))
    parser.add_argument("--no-history", action="store_true", help=t("cli.no_history"))
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    gtux_log.setup(debug=args.debug)

    try:
        return run(args)
    except KeyboardInterrupt:
        return 130
    except Exception:
        log.exception("unhandled error")
        print(t("cli.crashed", path=gtux_log.log_path()), file=sys.stderr)
        raise


def run(args) -> int:
    if args.gui:
        try:
            from gtux.gui import app
        except (ImportError, ValueError) as e:  # ValueError: gi.require_version не нашёл GTK4/Adw
            log.error("GUI unavailable: %s", e)
            print(t("gui.need_gtk", error=e), file=sys.stderr)
            return 2
        # без --lang окно возьмёт сохранённый язык
        return app.run(args.lang, save_history=not args.no_history)

    i18n.set_language(args.lang or i18n.DEFAULT)
    if args.update_kb:
        return update_kb()
    if args.install_ge:
        return install_ge(Path(args.install_ge).expanduser())
    from gtux import fixer, history
    from gtux.checks import ALL_GROUPS
    from gtux.models import Context, Status
    from gtux.runner import run_all

    ctx = Context(verify_packages=True)
    results = run_all(ALL_GROUPS, ctx)
    if args.library:
        return show_library(ctx)

    if args.json:
        from gtux.output import json_out
        print(json_out.render(results, fixer.build_plan(results, ctx)))
    elif args.report:
        from gtux.output import report
        print(report.render(results))
    else:
        try:
            from gtux.output import fix_ui, terminal
        except ImportError:
            print(t("cli.need_rich"), file=sys.stderr)
            return 2
        previous = history.load_latest()
        changes = history.diff(previous, results)
        if not args.no_history:
            history.save(results)
        terminal.render(results, show_fix_hint=not args.fix, changes=changes,
                        previous_time=previous.get("time") if previous else None)
        if args.fix:
            return fix_ui.run(results, ctx, recheck=lambda: run_all(ALL_GROUPS, Context(verify_packages=True)))

    return 1 if any(r.status == Status.FAIL for r in results) else 0



def show_library(ctx) -> int:
    """Вся библиотека Steam в терминале: та же сводка, что на странице «Библиотека» в окне."""
    from rich.console import Console
    from rich.table import Table

    from gtux import knowledge, library
    games = library.scan([root for _, root in ctx.steam_roots], ctx.steam_libraries, knowledge.profile_from(ctx))
    if not games:
        print(t("gui.library.empty"))
        return 1
    colors = {"ok": "green", "warn": "yellow", "fail": "red", "unknown": "bright_black"}
    table = Table(title=t("gui.library.title"), show_lines=False)
    table.add_column("", width=2)
    table.add_column(t("gui.launch.game"))
    table.add_column("")
    for game in games:
        status, parts = library.summary(game)
        table.add_row(f"[{colors[status.value]}]●[/]", game.name, " · ".join(parts))
    Console().print(table)
    return 0


def install_ge(target: Path) -> int:
    """Скачать свежий GE-Proton в compatibilitytools.d (вызывается и из «Исправить…»)."""
    from gtux import geproton

    def progress(done, total):
        extra = " " + t("gui.kb.mb", done=f"{done / 1e6:.0f}", total=f"{total / 1e6:.0f}") if total else ""
        print(f"\r{t('ge.download')}{extra}" + " " * 10, end="", flush=True)

    try:
        release = geproton.latest_release()
        print(t("ge.found", tag=release["tag"], target=target))
        path = geproton.install(target, progress, release)
    except (OSError, ValueError, geproton.GEError) as e:
        log.exception("GE-Proton install failed")
        print(f"\n{t('ge.failed', error=f'{type(e).__name__}: {e}')}", file=sys.stderr)
        return 1
    print("\n" + t("ge.done", path=path))
    return 0


def update_kb() -> int:
    """Скачать базу знаний ProtonDB (интернет нужен только здесь)."""
    from gtux import gamedb, knowledge
    from gtux.checks import steam

    libraries = []
    for _, root in steam.find_roots():
        try:
            libraries += steam.read_libraries(root)
        except (OSError, ValueError):
            pass
    appids = [g.appid for g in gamedb.installed_games([lib for lib in libraries if lib.exists()])]
    print(t("kb.intro"))

    def progress(stage, done=0, total=0):
        extra = f" {done / 1e6:.0f}/{total / 1e6:.0f} MB" if stage == "download" and total else (
            f" {done}/{total}" if total else "")
        print(f"\r{t('gui.kb.stage.' + stage)}{extra}" + " " * 10, end="", flush=True)

    try:
        data = knowledge.update(appids, progress)
    except Exception as e:  # noqa: BLE001 — сеть, GitHub, формат
        log.exception("knowledge update failed")
        print(f"\n{t('gui.kb.failed', error=f'{type(e).__name__}: {e}')}", file=sys.stderr)
        return 1
    print("\n" + t("gui.kb.done", games=len(data["games"])))
    print(knowledge.LICENSE)
    return 0
