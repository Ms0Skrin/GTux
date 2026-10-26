"""Командная строка: linux-gamer-doctor [--gui | --fix | --json | --report] [--lang ru|en] [--debug]

Copyright (C) 2026 Евгений
SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import logging
import sys

from doctor import __version__, i18n
from doctor import log as doctor_log
from doctor.i18n import t

log = logging.getLogger("doctor.main")


def main() -> int:
    parser = argparse.ArgumentParser(prog="linux-gamer-doctor", description=t("cli.description"),
                                     epilog=t("cli.log_epilog", path=doctor_log.log_path()))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help=t("cli.gui"))
    mode.add_argument("--fix", action="store_true", help=t("cli.fix"))
    mode.add_argument("--json", action="store_true", help=t("cli.json"))
    mode.add_argument("--report", action="store_true", help=t("cli.report"))
    parser.add_argument("--lang", choices=i18n.AVAILABLE, default=None, help=t("cli.lang"))
    parser.add_argument("--debug", action="store_true", help=t("cli.debug"))
    parser.add_argument("--no-history", action="store_true", help=t("cli.no_history"))
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    doctor_log.setup(debug=args.debug)

    try:
        return run(args)
    except KeyboardInterrupt:
        return 130
    except Exception:
        log.exception("unhandled error")
        print(t("cli.crashed", path=doctor_log.log_path()), file=sys.stderr)
        raise


def run(args) -> int:
    if args.gui:
        try:
            from doctor.gui import app
        except (ImportError, ValueError) as e:  # ValueError: gi.require_version не нашёл GTK4/Adw
            log.error("GUI unavailable: %s", e)
            print(t("gui.need_gtk", error=e), file=sys.stderr)
            return 2
        # без --lang окно возьмёт сохранённый язык
        return app.run(args.lang, save_history=not args.no_history)

    i18n.set_language(args.lang or i18n.DEFAULT)
    from doctor import fixer, history
    from doctor.checks import ALL_GROUPS
    from doctor.models import Context, Status
    from doctor.runner import run_all

    ctx = Context()
    results = run_all(ALL_GROUPS, ctx)

    if args.json:
        from doctor.output import json_out
        print(json_out.render(results, fixer.build_plan(results, ctx)))
    elif args.report:
        from doctor.output import report
        print(report.render(results))
    else:
        try:
            from doctor.output import fix_ui, terminal
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
            return fix_ui.run(results, ctx, recheck=lambda: run_all(ALL_GROUPS, Context()))

    return 1 if any(r.status == Status.FAIL for r in results) else 0

