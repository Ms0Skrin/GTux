"""Исправление «одной кнопкой».

Умеет: ставить пакеты, включать i386 на Debian/Ubuntu, записывать настройки ядра в /etc/sysctl.d
и открывать Flatpak-Steam доступ к папкам. Остальное (pacman.conf, параметры ядра) остаётся ручным:
такие команды мы показываем, но не выполняем.
Ничего не запускается без явного подтверждения пользователя.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field

from doctor.models import Action, CheckResult, Context, Status
from doctor.packages import Apt, Pacman

PROBLEMS = (Status.FAIL, Status.WARN, Status.UNKNOWN)
PACKAGE_KINDS = ("enable_i386", "install")


@dataclass
class Step:
    kind: str                       # "enable_i386" | "install" | "sysctl" | "flatpak_filesystem"
    argv: list[str]
    packages: list[str] = field(default_factory=list)
    path: str = ""                  # sysctl: файл, который записываем перед argv
    content: str = ""               # sysctl: его содержимое
    title: str = ""                 # для действий: название проверки, которую исправляем

    @property
    def root(self) -> bool:
        return bool(self.argv) and self.argv[0] == "sudo"

    @property
    def command(self) -> str:
        if self.kind == "sysctl":
            return f"echo {shlex.quote(self.content)} | sudo tee {shlex.quote(self.path)} && {shlex.join(self.argv)}"
        return shlex.join(self.argv)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "command": self.command, "argv": self.argv, "packages": self.packages,
                "title": self.title}


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
        if r.status in PROBLEMS:
            pkgs += [p for p in r.packages if p not in pkgs]
    return pkgs


def action_step(action: Action, title: str = "") -> Step | None:
    if action.kind == "sysctl":
        return Step("sysctl", ["sudo", "sysctl", f"--load={action.target}"],
                    path=action.target, content=action.value, title=title)
    if action.kind == "flatpak_filesystem":
        return Step("flatpak_filesystem",
                    ["flatpak", "override", "--user", f"--filesystem={action.target}", action.value], title=title)
    return None


def build_plan(results: list[CheckResult], ctx: Context, only: list[str] | None = None) -> Plan:
    plan = Plan()
    pm = ctx.package_manager
    pkgs = wanted_packages(results) if only is None else only
    if pm is not None and pkgs:
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

    seen: set[str] = set()
    for r in results:
        if r.status not in PROBLEMS:
            continue
        for action in r.actions:
            step = action_step(action, r.title)
            if step is not None and step.command not in seen:
                seen.add(step.command)
                plan.steps.append(step)
    return plan


def gui_argv(step: Step, pm) -> list[str]:
    """Команда без sudo и без вопросов в терминале: в окне подтверждение уже получено."""
    argv = list(step.argv[1:] if step.root else step.argv)
    if step.kind == "install" and pm is not None and pm.assume_yes:
        argv.insert(len(argv) - len(step.packages), pm.assume_yes)
    return argv


def root_script(steps: list[Step], pm) -> str:
    """Все шаги с правами root одним сценарием sh — чтобы пароль спросили один раз."""
    lines = ["set -ex"]
    for step in steps:
        if not step.root:
            continue
        if step.kind == "sysctl":
            lines.append(f"printf '%s\\n' {shlex.quote(step.content)} > {shlex.quote(step.path)}")
        lines.append(shlex.join(gui_argv(step, pm)))
    return "\n".join(lines)


def _commands(step: Step) -> list[tuple[list[str], str | None]]:
    """Что запустить для шага в терминале: (argv, что подать на вход)."""
    if step.kind == "sysctl":
        return [(["sudo", "tee", step.path], step.content + "\n"), (step.argv, None)]
    return [(step.argv, None)]


def execute(plan: Plan, echo) -> tuple[bool, Step | None, int]:
    """Выполняет шаги по очереди с выводом прямо в терминал. Останавливается на первой ошибке.

    echo(step) вызывается перед каждым шагом. Возвращает (успех, упавший шаг, код возврата).
    """
    for step in plan.steps:
        echo(step)
        for argv, stdin in _commands(step):
            try:
                code = subprocess.run(argv, input=stdin, text=True,
                                      stdout=subprocess.DEVNULL if stdin else None).returncode
            except OSError as e:
                echo(None, error=str(e))
                return False, step, -1
            if code != 0:
                return False, step, code
    return True, None, 0
