"""Исправление «одной кнопкой».

Умеет: ставить пакеты, включать i386 на Debian/Ubuntu, записывать настройки ядра в /etc/sysctl.d
и открывать Flatpak-Steam доступ к папкам. Остальное (pacman.conf, параметры ядра) остаётся ручным:
такие команды мы показываем, но не выполняем.

«По желанию» (plan.offers): программы, без которых можно жить, — Lutris, protontricks, Heroic и Faugus
(Flathub, --user, без пароля), GE-Proton (скачивает сама программа: gtux --install-ge). Их мы только
предлагаем: в окне галочка снята, в терминале они не входят в «да».
Ничего не запускается без явного подтверждения пользователя.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from gtux.models import Action, CheckResult, Context, Status
from gtux.packages import Apt, Pacman

PROBLEMS = (Status.FAIL, Status.WARN, Status.UNKNOWN)
PACKAGE_KINDS = ("enable_i386", "install")
FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
# «Подготовить всё для игр»: какие пункты «по желанию» отмечаются сразу. Полное обновление системы и
# protontricks — нет: они для конкретных случаев (рассинхрон драйвера, лог конкретной игры).
SETUP_KINDS = {"install", "flatpak_app", "ge_proton", "enable_multilib"}


@dataclass
class Step:
    kind: str                       # "enable_i386" | "install" | "sysctl" | "flatpak_filesystem"
                                    # | "flatpak_app" | "ge_proton"
    argv: list[str]
    packages: list[str] = field(default_factory=list)
    path: str = ""                  # sysctl: файл, который записываем перед argv
    content: str = ""               # sysctl: его содержимое
    title: str = ""                 # для действий: название проверки, которую исправляем
    optional: bool = False          # «по желанию»: сами не отмечаем
    prereq: list["Step"] = field(default_factory=list)  # что сделать до (например, поставить flatpak)
    then: list["Step"] = field(default_factory=list)    # что сделать после (пакеты после включения multilib)
    warning: str = ""               # ключ перевода: чем рискованно
    backup: str = ""                # enable_multilib: куда сохранить копию файла
    sha256: str = ""                # enable_multilib: файл должен быть ровно таким, каким мы его проверяли
    pre: list[list[str]] = field(default_factory=list)  # команды без root перед argv (flathub remote-add)

    @property
    def root(self) -> bool:
        return bool(self.argv) and self.argv[0] == "sudo"

    @property
    def command(self) -> str:
        if self.kind == "enable_multilib":
            return " && ".join([f"echo {shlex.quote(self.sha256 + '  ' + self.path)} | sha256sum -c --quiet",
                                shlex.join(["sudo", "cp", "-a", self.path, self.backup]), shlex.join(self.argv)])
        if self.kind == "sysctl":
            return f"echo {shlex.quote(self.content)} | sudo tee {shlex.quote(self.path)} && {shlex.join(self.argv)}"
        return " && ".join(shlex.join(a) for a in [*self.pre, self.argv])

    def chain(self) -> list["Step"]:
        """Шаг вместе с тем, что нужно сделать до и после него."""
        return [*self.prereq, self, *self.then]

    def to_dict(self) -> dict:
        return {"kind": self.kind, "command": self.command, "argv": self.argv, "packages": self.packages,
                "title": self.title, "optional": self.optional, "warning": self.warning,
                "prereq": [p.to_dict() for p in self.prereq], "then": [p.to_dict() for p in self.then]}


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # пакеты, которые поставить автоматически нельзя
    skipped_reason: str = ""                           # ключ перевода
    offers: list[Step] = field(default_factory=list)   # «по желанию»: не выполняются без отдельного выбора
    unavailable: list[str] = field(default_factory=list)  # нет в подключённых репозиториях
    unavailable_hint: str = ""                            # ключ перевода: какой репозиторий включить

    def to_dict(self) -> dict:
        return {"steps": [s.to_dict() for s in self.steps], "skipped": self.skipped,
                "skipped_reason": self.skipped_reason, "offers": [s.to_dict() for s in self.offers],
                "unavailable": self.unavailable, "unavailable_hint": self.unavailable_hint}


def wanted_packages(results: list[CheckResult]) -> list[str]:
    pkgs: list[str] = []
    for r in results:
        if r.status in PROBLEMS:
            pkgs += [p for p in r.packages if p not in pkgs]
    return pkgs


def gtux_argv(*args: str) -> list[str]:
    """Запуск самой программы: работает и из пакета, и из папки с исходниками."""
    return [sys.executable, "-m", "gtux", *args]


def action_step(action: Action, title: str = "", ctx: Context | None = None) -> Step | None:
    pm = ctx.package_manager if ctx else None
    if action.kind == "package":
        if pm is None:
            return None
        if ctx is not None and ctx.verify_packages and pm.unavailable([action.target]):
            # пакета нет в подключённых репозиториях — та же программа с Flathub, если она там есть
            return action_step(Action("flatpak_app", action.value, optional=action.optional), title, ctx) \
                if action.value else None
        return Step("install", pm.install_argv([action.target]), [action.target], title=title,
                    optional=action.optional)
    if action.kind == "flatpak_app":
        step = Step("flatpak_app", ["flatpak", "install", "--user", "--noninteractive", "flathub", action.target],
                    title=title, optional=action.optional,
                    pre=[["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB]])
        if not (ctx and ctx.flatpak_apps is not None):  # flatpak не установлен — ставим его пакетом
            if pm is None:
                return None
            names = flatpak_package(ctx)
            step.prereq = [Step("install", pm.install_argv(names), names)]
        return step
    if action.kind == "pacman_multilib":
        return multilib_step(action.target, [int(n) for n in action.value.split(",")], title)
    if action.kind == "system_upgrade":
        return Step("system_upgrade", ["sudo", "pacman", "-Syu"], title=title, optional=action.optional,
                    warning="fix.warn.system_upgrade")
    if action.kind == "protontricks":
        return Step("protontricks", ["protontricks", action.target, "-q", *action.value.split()],
                    title=title, optional=action.optional, warning="fix.warn.protontricks")
    if action.kind == "ge_proton":
        return Step("ge_proton", gtux_argv("--install-ge", action.target), title=title, optional=action.optional)
    if action.kind == "sysctl":
        return Step("sysctl", ["sudo", "sysctl", f"--load={action.target}"],
                    path=action.target, content=action.value, title=title)
    if action.kind == "flatpak_filesystem":
        return Step("flatpak_filesystem",
                    ["flatpak", "override", "--user", f"--filesystem={action.target}", action.value], title=title)
    return None


def multilib_step(path: str, lines: list[int], title: str = "") -> Step | None:
    """Включить [multilib]: раскомментировать строки lines в pacman.conf (с копией) и обновить систему.
    Если файл не прочитать — шаг не предлагаем: без контрольной суммы править его вслепую нельзя."""
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None
    script = ";".join(f"{n}s/^[[:space:]]*#[[:space:]]*//" for n in lines)
    return Step("enable_multilib", ["sudo", "sed", "-i", script, path], path=path, title=title, optional=True,
                backup=f"{path}.gtux-{time.strftime('%Y%m%d-%H%M%S')}", sha256=digest,
                warning="fix.warn.multilib",
                then=[Step("system_upgrade", ["sudo", "pacman", "-Syu"], warning="fix.warn.system_upgrade")])


def flatpak_package(ctx: Context) -> list[str]:
    from gtux.packages import component
    return component(ctx, "flatpak") or ["flatpak"]


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
        if pkgs and ctx.verify_packages:
            missing = pm.unavailable(pkgs) or []
            if missing:
                plan.unavailable = missing
                plan.unavailable_hint = f"fix.unavailable.{pm.family}"
                pkgs = [p for p in pkgs if p not in missing]
                # 32-битное нечего ставить — и включать i386 незачем
                if not any(pm.is_32bit(p) for p in pkgs):
                    plan.steps = [s for s in plan.steps if s.kind != "enable_i386"]
        if pkgs:
            plan.steps.append(Step("install", pm.install_argv(pkgs), pkgs))

    seen: set[str] = set()
    for r in results:
        for action in r.actions:
            if not action.optional and r.status not in PROBLEMS:
                continue
            step = action_step(action, r.title, ctx)
            if step is not None and step.command not in seen:
                seen.add(step.command)
                (plan.offers if action.optional else plan.steps).append(step)
    # включение multilib заодно ставит то, что из-за него пропустили
    for step in plan.offers:
        if step.kind == "enable_multilib" and plan.skipped and pm is not None:
            step.then.append(Step("install", pm.install_argv(plan.skipped), list(plan.skipped)))
    return plan


def user_commands(step: Step) -> list[list[str]]:
    """Команды шага без root, по порядку."""
    return [*step.pre, step.argv]


def step_env(step: Step) -> dict[str, str] | None:
    """Окружение для шага: GE-Proton ставит сама программа, ей нужен путь к своему пакету."""
    if step.kind != "ge_proton":
        return None
    root = str(Path(__file__).resolve().parent.parent)
    return {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [root, os.environ.get("PYTHONPATH")]))}


def gui_argv(step: Step, pm) -> list[str]:
    """Команда без sudo и без вопросов в терминале: в окне подтверждение уже получено."""
    argv = list(step.argv[1:] if step.root else step.argv)
    if step.kind == "install" and pm is not None and pm.assume_yes:
        argv.insert(len(argv) - len(step.packages), pm.assume_yes)
    if step.kind == "system_upgrade" and pm is not None and pm.assume_yes:
        argv.append(pm.assume_yes)
    return argv


def root_script(steps: list[Step], pm) -> str:
    """Все шаги с правами root одним сценарием sh — чтобы пароль спросили один раз."""
    lines = ["set -ex"]
    for step in steps:
        if not step.root:
            continue
        if step.kind == "sysctl":
            lines.append(f"printf '%s\\n' {shlex.quote(step.content)} > {shlex.quote(step.path)}")
        if step.kind == "enable_multilib":
            # файл изменился после проверки — sha256sum вернёт ошибку, и set -e остановит всё
            lines.append(f"printf '%s\\n' {shlex.quote(step.sha256 + '  ' + step.path)} | sha256sum -c --quiet")
            lines.append(shlex.join(["cp", "-a", step.path, step.backup]))
        lines.append(shlex.join(gui_argv(step, pm)))
    return "\n".join(lines)


def _commands(step: Step) -> list[tuple[list[str], str | None]]:
    """Что запустить для шага в терминале: (argv, что подать на вход)."""
    if step.kind == "sysctl":
        return [(["sudo", "tee", step.path], step.content + "\n"), (step.argv, None)]
    if step.kind == "enable_multilib":
        return [(["sha256sum", "-c", "--quiet", "-"], f"{step.sha256}  {step.path}\n"),
                (["sudo", "cp", "-a", step.path, step.backup], None), (step.argv, None)]
    return [(argv, None) for argv in user_commands(step)]


def execute(plan: Plan, echo) -> tuple[bool, Step | None, int]:
    """Выполняет шаги по очереди с выводом прямо в терминал. Останавливается на первой ошибке.

    echo(step) вызывается перед каждым шагом. Возвращает (успех, упавший шаг, код возврата).
    """
    for step in [st for s in plan.steps for st in s.chain()]:
        echo(step)
        for argv, stdin in _commands(step):
            try:
                code = subprocess.run(argv, input=stdin, text=True, env=step_env(step),
                                      stdout=subprocess.DEVNULL if stdin else None).returncode
            except OSError as e:
                echo(None, error=str(e))
                return False, step, -1
            if code != 0:
                return False, step, code
    return True, None, 0


def setup_offers(plan: Plan) -> list[Step]:
    """Пункты «по желанию», которые «Подготовить всё для игр» отмечает сразу."""
    return [s for s in plan.offers if s.kind in SETUP_KINDS]
