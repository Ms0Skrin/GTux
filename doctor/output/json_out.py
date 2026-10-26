"""Машинно-читаемый вывод для бота, GUI и скриптов."""

from __future__ import annotations

import json

from doctor import __version__
from doctor.fixer import Plan
from doctor.i18n import current_language
from doctor.models import CheckResult
from doctor.runner import summarize


def render(results: list[CheckResult], plan: Plan | None = None) -> str:
    data = {
        "version": __version__,
        "language": current_language(),
        "summary": summarize(results),
        "results": [r.to_dict() for r in results],
        "fix_plan": plan.to_dict() if plan else None,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
