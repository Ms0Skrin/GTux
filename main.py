#!/usr/bin/env python3
"""Запуск из папки проекта без установки: python main.py [--gui | --fix | --json | --report]"""

import sys

if sys.version_info < (3, 11):
    sys.exit(f"Нужен Python 3.11 или новее, а у вас {sys.version.split()[0]}.")

from gtux.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
