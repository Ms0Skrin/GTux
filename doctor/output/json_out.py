"""Машинно-читаемый вывод для бота, GUI и скриптов."""

from __future__ import annotations

import json

from doctor import __version__
from doctor.i18n import current_language
from doctor.models import CheckResult
from doctor.runner import summarize


def render(results: list[CheckResult]) -> str:
    data = {
        "version": __version__,
        "language": current_language(),
        "summary": summarize(results),
        "results": [r.to_dict() for r in results],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
