"""Конструктор параметров запуска Steam: галочки -> готовая строка с %command%.

Источники:
  - переменные Proton: README Proton (PROTON_LOG, PROTON_NO_FSYNC, PROTON_NO_ESYNC, PROTON_USE_WINED3D)
  - DXVK_HUD: README DXVK
  - gamescope: `gamescope --help` (-W/-H, -f, --mangoapp вместо mangohud внутри gamescope, «--» перед командой)
  - WINE_CPU_TOPOLOGY: формат «N:id,id,…» (см. doctor/checks/games.py)
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass


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
