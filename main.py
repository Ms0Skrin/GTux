#!/usr/bin/env python3
"""Точка входа: python main.py [--json] [--lang ru]"""

import sys

if sys.version_info < (3, 11):
    sys.exit(f"Нужен Python 3.11 или новее, а у вас {sys.version.split()[0]}.")

import argparse  # noqa: E402

from doctor import __version__, i18n  # noqa: E402
from doctor.checks import ALL_GROUPS  # noqa: E402
from doctor.i18n import t  # noqa: E402
from doctor.models import Context, Status  # noqa: E402
from doctor.runner import run_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(prog="main.py", description=t("cli.description"))
    parser.add_argument("--json", action="store_true", help=t("cli.json"))
    parser.add_argument("--lang", choices=i18n.AVAILABLE, default=i18n.DEFAULT, help=t("cli.lang"))
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    i18n.set_language(args.lang)

    results = run_all(ALL_GROUPS, Context())

    if args.json:
        from doctor.output import json_out
        print(json_out.render(results))
    else:
        try:
            from doctor.output import terminal
        except ImportError:
            print(t("cli.need_rich"), file=sys.stderr)
            return 2
        terminal.render(results)

    return 1 if any(r.status == Status.FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
