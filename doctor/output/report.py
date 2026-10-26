"""Отчёт в Markdown — чтобы вставить на форум или в чат, когда просишь помощи."""

from __future__ import annotations

import time
from pathlib import Path

from doctor import __version__
from doctor.i18n import t
from doctor.models import CheckResult, Status
from doctor.runner import summarize

MARK = {Status.OK: "✅", Status.WARN: "⚠️", Status.FAIL: "❌", Status.UNKNOWN: "❔"}


def _private(text: str) -> str:
    """Домашняя папка -> ~, чтобы не светить имя пользователя."""
    return text.replace(str(Path.home()), "~")


def _cell(text: str) -> str:
    return _private(text).replace("|", "\\|").replace("\n", "<br>")


def render(results: list[CheckResult]) -> str:
    by_id = {r.id: r.value for r in results}
    s = summarize(results)
    lines = [
        f"## {t('app.title')} — {t('report.title')}",
        "",
        f"- **{t('distro.os.title')}:** {by_id.get('distro.os', '?')}",
        f"- **{t('distro.kernel.title')}:** {by_id.get('distro.kernel', '?')}",
        f"- **{t('gpu.detect.title')}:** {by_id.get('gpu.detect', '?')}",
    ]
    driver = by_id.get("gpu.nvidia_version") or by_id.get("gpu.mesa_version")
    if driver:
        lines.append(f"- **{t('report.driver')}:** {driver}")
    lines += [
        f"- **{t('report.summary')}:** ✅ {s['ok']} · ⚠️ {s['warn']} · ❌ {s['fail']} · ❔ {s['unknown']}",
        "",
    ]

    problems = [r for r in results if r.status != Status.OK]
    if problems:
        lines += [f"### {t('report.problems')}", ""]
        for r in sorted(problems, key=lambda r: [Status.FAIL, Status.WARN, Status.UNKNOWN].index(r.status)):
            lines.append(f"- {MARK[r.status]} **{_private(r.title)}** — {_private(r.value).replace(chr(10), '; ')}")
            for extra in (r.hint, r.error):
                if extra:
                    lines.append(f"  - {_private(extra).replace(chr(10), ' ')}")
        lines.append("")

    lines += [f"<details><summary>{t('report.all_checks')}</summary>", "",
              f"| | {t('ui.col.check')} | {t('ui.col.result')} |", "|---|---|---|"]
    for r in results:
        lines.append(f"| {MARK[r.status]} | {_cell(r.title)} | {_cell(r.value or '—')} |")
    lines += ["", "</details>", "",
              f"<sub>{t('report.footer', version=__version__, date=time.strftime('%Y-%m-%d'))}</sub>"]
    return "\n".join(lines)
