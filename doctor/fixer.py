"""Установка недостающего «одной кнопкой».

Только пакеты и включение i386 на Debian/Ubuntu. Правка конфигов (pacman.conf, sysctl) остаётся
ручной: такие команды мы показываем, но не выполняем.
Ничего не запускается без явного «да» пользователя в терминале.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field

from doctor.models import CheckResult, Context, Status
from doctor.packages import Apt, Pacman


@dataclass
class Step:
    kind: str                       # "enable_i386" | "install"
    argv: list[str]
    packages: list[str] = field(default_factory=list)

    @property
    def command(self) -> str:
        return shlex.join(self.argv)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "command": self.command, "argv": self.argv, "packages": self.packages}


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # пакеты, которые поставить автоматически нельзя
    skipped_reason: str = ""                           # ключ перевода

    def to_dict(self) -> dict:
        return {"steps": [s.to_dict() for s in self.steps], "skipped": self.skipped,
                "skipped_reason": self.skipped_reason}


def wanted_packages(results: list[CheckResult]) -> list[str]:
    pkgs: list[str] = []
    for r in results:
        if r.status in (Status.FAIL, Status.WARN, Status.UNKNOWN):
            pkgs += [p for p in r.packages if p not in pkgs]
    return pkgs


def build_plan(results: list[CheckResult], ctx: Context, only: list[str] | None = None) -> Plan:
    plan = Plan()
    pm = ctx.package_manager
    pkgs = wanted_packages(results) if only is None else only
    if pm is None or not pkgs:
        return plan

    lib32 = [p for p in pkgs if pm.is_32bit(p)]
    if lib32 and ctx.multilib_enabled is False:
        if isinstance(pm, Apt):
            plan.steps.append(Step("enable_i386", ["sudo", "dpkg", "--add-architecture", "i386"]))
            plan.steps.append(Step("enable_i386", ["sudo", "apt", "update"]))
        elif isinstance(pm, Pacman):
            # [multilib] включается правкой /etc/pacman.conf — это делаем только руками.
            plan.skipped, plan.skipped_reason = lib32, "fix.skip.multilib"
            pkgs = [p for p in pkgs if p not in lib32]
    if pkgs:
        plan.steps.append(Step("install", pm.install_argv(pkgs), pkgs))
    return plan


def gui_argv(step: Step, pm) -> list[str]:
    """Команда для окна: pkexec вместо sudo (графический запрос пароля) и без вопросов в терминале."""
    argv = list(step.argv)
    if argv and argv[0] == "sudo":
        argv[0] = "pkexec"
    if step.kind == "install" and pm is not None and pm.assume_yes:
        argv.insert(len(argv) - len(step.packages), pm.assume_yes)
    return argv


def execute(plan: Plan, echo) -> tuple[bool, Step | None, int]:
    """Выполняет шаги по очереди с выводом прямо в терминал. Останавливается на первой ошибке.

    echo(step) вызывается перед каждым шагом. Возвращает (успех, упавший шаг, код возврата).
    """
    for step in plan.steps:
        echo(step)
        try:
            code = subprocess.run(step.argv).returncode
        except OSError as e:
            echo(None, error=str(e))
            return False, step, -1
        if code != 0:
            return False, step, code
    return True, None, 0
