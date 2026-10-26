"""Переводы. Все тексты интерфейса лежат в doctor/i18n/<язык>.py в словаре TEXTS.

Чтобы добавить язык: скопировать ru.py в en.py, перевести значения и добавить код в AVAILABLE.
"""

from __future__ import annotations

from importlib import import_module

AVAILABLE = ("ru",)
DEFAULT = "ru"

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
