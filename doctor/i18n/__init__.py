"""Переводы. Все тексты интерфейса лежат в doctor/i18n/<язык>.py в словаре TEXTS.

Чтобы добавить язык: скопировать en.py в <код>.py, перевести значения и добавить код в AVAILABLE.
Язык по умолчанию берётся из локали системы (LANG и др.).
"""

from __future__ import annotations

import os
from importlib import import_module

AVAILABLE = ("ru", "en")


def system_language() -> str:
    """Язык по переменным окружения: ru для русской локали, иначе en."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return "ru" if value.lower().startswith(("ru", "uk", "be")) else "en"
    return "en"


DEFAULT = system_language()

_texts: dict[str, str] = {}
_lang = DEFAULT


def set_language(lang: str) -> None:
    global _texts, _lang
    if lang not in AVAILABLE:
        raise ValueError(f"unknown language: {lang}")
    _texts = import_module(f"doctor.i18n.{lang}").TEXTS
    _lang = lang


def current_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    """Текст по ключу. Если ключа нет — возвращаем сам ключ, чтобы пропуск было видно."""
    text = _texts.get(key, key)
    return text.format(**kwargs) if kwargs else text


set_language(DEFAULT)
