"""Конструктор параметров запуска Steam: галочки -> готовая строка с %command%.

Источники:
  - переменные Proton: README Proton (PROTON_LOG, PROTON_NO_FSYNC, PROTON_NO_ESYNC, PROTON_USE_WINED3D)
  - DXVK_HUD: README DXVK
  - gamescope: `gamescope --help` (-W/-H, -f, --mangoapp вместо mangohud внутри gamescope, «--» перед командой)
  - WINE_CPU_TOPOLOGY: формат «N:id,id,…» (см. gtux/checks/games.py)
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field


@dataclass
class LaunchConfig:
    gamemode: bool = False
    mangohud: bool = False
    gamescope: bool = False
    gamescope_width: int = 0      # 0 — не задавать
    gamescope_height: int = 0
    gamescope_fullscreen: bool = True
    dxvk_hud: bool = False
    proton_log: bool = False
    no_fsync: bool = False
    no_esync: bool = False
    wined3d: bool = False
    cpu_cores: int = 0            # 0 — не ограничивать
    game_args: str = ""


def build(cfg: LaunchConfig) -> str:
    env = []
    if cfg.dxvk_hud:
        env.append("DXVK_HUD=fps")
    if cfg.proton_log:
        env.append("PROTON_LOG=1")
    if cfg.no_fsync:
        env.append("PROTON_NO_FSYNC=1")
    if cfg.no_esync:
        env.append("PROTON_NO_ESYNC=1")
    if cfg.wined3d:
        env.append("PROTON_USE_WINED3D=1")
    if cfg.cpu_cores > 0:
        env.append(f"WINE_CPU_TOPOLOGY={cfg.cpu_cores}:{','.join(map(str, range(cfg.cpu_cores)))}")

    parts = env[:]
    if cfg.gamescope:
        parts.append("gamescope")
        if cfg.gamescope_width and cfg.gamescope_height:
            parts += ["-W", str(cfg.gamescope_width), "-H", str(cfg.gamescope_height)]
        if cfg.gamescope_fullscreen:
            parts.append("-f")
        if cfg.mangohud:
            parts.append("--mangoapp")  # так советует сам gamescope вместо mangohud внутри него
        parts.append("--")
    if cfg.gamemode:
        parts.append("gamemoderun")
    if cfg.mangohud and not cfg.gamescope:
        parts.append("mangohud")
    parts.append("%command%")
    line = " ".join(parts)
    args = cfg.game_args.strip()
    if args:
        # аргументы игры пишем как есть, но проверяем, что кавычки закрыты
        shlex.split(args)
        line += " " + args
    return line


# ---------------- разбор готовой строки ----------------
# Обёртки, которые запускают команду дальше («обёртка %command%»). gamescope разбираем отдельно:
# у него свои аргументы до «--».
KNOWN_WRAPPERS = ("gamemoderun", "mangohud", "game-performance", "prime-run")
ENV_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)


@dataclass
class Parsed:
    env: dict[str, str] = field(default_factory=dict)
    gamescope: list[str] = field(default_factory=list)  # «gamescope … --» целиком или пусто
    wrappers: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)       # аргументы игры после %command%


def parse(opts: str) -> Parsed | None:
    """Разбирает строку параметров. None — строка сложнее, чем мы умеем безопасно править
    (команды оболочки, неизвестные программы, несколько %command%)."""
    try:
        tokens = shlex.split(opts)
    except ValueError:
        return None
    p = Parsed()
    if "%command%" not in tokens:
        # Без %command% Steam передаёт всё игре как аргументы.
        if all(tok.startswith(("-", "+")) for tok in tokens):
            p.args = tokens
            return p
        return None
    if tokens.count("%command%") != 1:
        return None
    i = tokens.index("%command%")
    before, p.args = tokens[:i], tokens[i + 1:]
    if any(tok in ("|", "&", ";", "&&", "||") or "$" in tok or "`" in tok for tok in p.args):
        return None
    j = 0
    while j < len(before):
        tok = before[j]
        m = ENV_ASSIGN.match(tok)
        if m:
            p.env[m[1]] = m[2]
        elif tok == "gamescope" and not p.gamescope and "--" in before[j:]:
            end = before.index("--", j)
            p.gamescope = before[j:end + 1]
            j = end
        elif tok in KNOWN_WRAPPERS:
            if tok not in p.wrappers:
                p.wrappers.append(tok)
        else:
            return None
        j += 1
    return p


def compose(p: Parsed) -> str:
    """Строка из разобранного: переменные, gamescope, обёртки, %command%, аргументы.
    Переменные всегда в начале: не все обёртки передают их дальше (game-performance — нет)."""
    parts = [f"{k}={shlex.quote(v)}" for k, v in p.env.items()]
    parts += [shlex.quote(t) for t in p.gamescope]
    parts += p.wrappers
    parts.append("%command%")
    parts += [shlex.quote(a) for a in p.args]
    return " ".join(parts)


def merge(base: Parsed, extra: Parsed) -> Parsed:
    """base + extra: переменные из extra перекрывают, обёртки и аргументы добавляются без повторов."""
    wrappers = base.wrappers + [w for w in extra.wrappers if w not in base.wrappers]
    order = {w: i for i, w in enumerate(KNOWN_WRAPPERS)}
    return Parsed(env={**base.env, **extra.env}, gamescope=extra.gamescope or base.gamescope,
                  wrappers=sorted(wrappers, key=lambda w: order.get(w, len(order))),
                  args=base.args + [a for a in extra.args if a not in base.args])


def config_from(p: Parsed) -> tuple[LaunchConfig, Parsed]:
    """Что из строки можно показать переключателями конструктора, и что останется «как есть»."""
    cfg, rest = LaunchConfig(), Parsed(env=dict(p.env), gamescope=list(p.gamescope),
                                       wrappers=list(p.wrappers), args=[])
    simple = {"PROTON_LOG": "proton_log", "PROTON_NO_FSYNC": "no_fsync", "PROTON_NO_ESYNC": "no_esync",
              "PROTON_USE_WINED3D": "wined3d"}
    for var, attr in simple.items():
        if rest.env.get(var) == "1":
            setattr(cfg, attr, True)
            del rest.env[var]
    if rest.env.get("DXVK_HUD") == "fps":
        cfg.dxvk_hud = True
        del rest.env["DXVK_HUD"]
    topo = re.fullmatch(r"(\d+):([\d,]+)", rest.env.get("WINE_CPU_TOPOLOGY", ""))
    if topo and topo[2] == ",".join(map(str, range(int(topo[1])))):
        cfg.cpu_cores = int(topo[1])
        del rest.env["WINE_CPU_TOPOLOGY"]
    for w, attr in (("gamemoderun", "gamemode"), ("mangohud", "mangohud")):
        if w in rest.wrappers:
            setattr(cfg, attr, True)
            rest.wrappers.remove(w)
    cfg.game_args = shlex.join(p.args)
    return cfg, rest
