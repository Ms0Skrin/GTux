"""GTux (доктор Linux-геймера): проверяет систему и объясняет, чего не хватает для игр.

Copyright (C) 2026 Евгений
SPDX-License-Identifier: GPL-3.0-or-later
"""

__version__ = "0.8.0"
__license__ = "GPL-3.0-or-later"


def command_name() -> str:
    """Как пользователь запустил программу — чтобы подсказки показывали правильную команду."""
    import sys
    return "python main.py" if sys.argv and sys.argv[0].endswith("main.py") else "gtux"
