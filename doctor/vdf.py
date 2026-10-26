"""Мини-парсер текстового формата Valve KeyValues (.vdf, .acf).

Формат: "ключ" "значение" или "ключ" { ... }; комментарии начинаются с //.
Для наших задач (libraryfolders.vdf, appmanifest, compatibilitytool.vdf) этого хватает.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])|//[^\n]*|(\S+)')


class VDFError(ValueError):
    pass


def _tokens(text: str):
    for m in _TOKEN.finditer(text):
        if m.group(1) is not None:
            yield "str", m.group(1).replace('\\\\', '\\').replace('\\"', '"')
        elif m.group(2) is not None:
            yield m.group(2), m.group(2)
        elif m.group(3) is not None:
            yield "str", m.group(3)  # значение без кавычек — встречается в старых файлах
        # иначе комментарий — пропускаем


def loads(text: str) -> dict:
    """Ключи сравниваются без учёта регистра у Valve, поэтому приводим их к нижнему."""
    root: dict = {}
    stack = [root]
    key: str | None = None
    for kind, val in _tokens(text):
        if kind == "str":
            if key is None:
                key = val.lower()
            else:
                stack[-1][key] = val
                key = None
        elif kind == "{":
            if key is None:
                raise VDFError("«{» без ключа")
            child: dict = {}
            stack[-1][key] = child
            stack.append(child)
            key = None
        elif kind == "}":
            if len(stack) == 1:
                raise VDFError("лишняя «}»")
            stack.pop()
    if len(stack) != 1:
        raise VDFError("не закрыта «{»")
    return root
