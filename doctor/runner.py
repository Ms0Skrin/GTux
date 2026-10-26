"""Запуск проверок.

Каждая проверка — функция с декоратором @check("id"). Если она падает с исключением,
мы не роняем программу, а превращаем ошибку в серый статус «не удалось проверить».
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Callable

from doctor.i18n import t
from doctor.models import CheckResult, Context, Status

log = logging.getLogger("doctor.runner")

CheckFunc = Callable[[Context], "CheckResult | list[CheckResult]"]


def check(check_id: str) -> Callable[[CheckFunc], CheckFunc]:
    def decorator(func: CheckFunc) -> CheckFunc:
        func.check_id = check_id  # type: ignore[attr-defined]
        return func

    return decorator


def result(group: str, check_id: str, status: Status, **kwargs) -> CheckResult:
    """Короткий способ собрать результат: заголовок берётся из переводов по ключу <group>.<id>.title."""
    kwargs.setdefault("title", t(f"{group}.{check_id}.title"))
    return CheckResult(id=f"{group}.{check_id}", group=group, status=status, **kwargs)


def run_all(groups, ctx: Context) -> list[CheckResult]:
    results: list[CheckResult] = []
    for module in groups:
        for func in module.CHECKS:
            started = time.monotonic()
            try:
                res = func(ctx)
            except Exception as e:  # noqa: BLE001 — любая ошибка проверки = серый статус
                log.exception("check %s.%s crashed", module.GROUP, func.check_id)
                res = result(
                    module.GROUP,
                    func.check_id,
                    Status.UNKNOWN,
                    value=t("common.crashed"),
                    error=f"{type(e).__name__}: {e}",
                )
            res = res if isinstance(res, list) else [res]
            log.debug("check %s.%s: %s in %.2fs", module.GROUP, func.check_id,
                      ",".join(r.status.value for r in res) or "-", time.monotonic() - started)
            results.extend(res)
    log.info("checks done: %s", summarize(results))
    return results


def summarize(results: list[CheckResult]) -> dict[str, int]:
    counts = Counter(r.status for r in results)
    return {s.value: counts.get(s, 0) for s in Status}
