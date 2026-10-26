"""Группа 10: установленные игры — чем запускаются, параметры запуска, античит, заметки из базы."""

from __future__ import annotations

import os
import re
import shlex

from gtux import gamedb, knowledge, launchers
from gtux.checks import disks
from gtux.checks.proton import installed_tool_names
from gtux.i18n import current_language, t
from gtux.models import Context, Status
from gtux.runner import check, result
from gtux.launchopts import merge, parse
from gtux.system import read_text, which

GROUP = "games"

SEVERITY = [Status.OK, Status.UNKNOWN, Status.WARN, Status.FAIL]
WRAPPERS = ("gamemoderun", "mangohud", "gamescope")
ENV_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# Статусы AreWeAntiCheatYet -> наш статус и ключ пояснения
ANTICHEAT = {
    "Supported": (Status.OK, "games.ac.supported"),
    "Running": (Status.OK, "games.ac.running"),
    "Planned": (Status.WARN, "games.ac.planned"),
    "Broken": (Status.WARN, "games.ac.broken"),
    "Denied": (Status.WARN, "games.ac.denied"),
}


def analyze_launch_options(opts: str, cpu_count: int | None = None) -> list[tuple[Status, str]]:
    """Ищет типичные ошибки в параметрах запуска Steam. Возвращает [(статус, пояснение)]."""
    try:
        tokens = shlex.split(opts)
    except ValueError:
        return [(Status.WARN, t("games.launch.quotes"))]
    before = tokens[:tokens.index("%command%")] if "%command%" in tokens else tokens
    env = {m[1]: m[2] for tok in before if (m := ENV_ASSIGN.match(tok))}
    wrappers = [tok for tok in before if tok in WRAPPERS]

    findings = []
    if (env or wrappers) and "%command%" not in opts:
        findings.append((Status.FAIL, t("games.launch.no_command")))
    for w in wrappers:
        if not which(w):
            findings.append((Status.FAIL, t("games.launch.missing_tool", tool=w)))

    return findings + env_findings(env, cpu_count)


def env_findings(env: dict[str, str], cpu_count: int | None = None) -> list[tuple[Status, str]]:
    """Проверки переменных окружения, общие для Steam и других лаунчеров."""
    findings = []
    topo = env.get("WINE_CPU_TOPOLOGY")
    if topo is not None:
        m = re.fullmatch(r"(\d+):(\d+(?:,\d+)*)", topo)
        ids = [int(x) for x in m[2].split(",")] if m else []
        cpus = cpu_count or os.cpu_count() or 0
        if not m or int(m[1]) != len(ids):
            findings.append((Status.WARN, t("games.launch.topology_format", value=topo)))
        elif cpus and max(ids) >= cpus:
            findings.append((Status.WARN, t("games.launch.topology_cpus", value=topo, cpus=cpus)))
    if env.get("PROTON_USE_WINED3D") == "1":
        findings.append((Status.WARN, t("games.launch.wined3d")))
    return findings


def _tool_is_known(name: str, installed: set[str]) -> bool:
    # Официальные сборки Valve (proton_experimental, proton_9 …) Steam докачивает сам.
    return name in installed or name.startswith(("proton_", "steamlinuxruntime"))


def assess_game(game: gamedb.Game, *, mapping: dict[str, str], options: dict[str, str],
                installed_tools: set[str], max_map_count: int | None,
                profile: knowledge.Profile | None = None) -> dict:
    note = gamedb.notes_db().get(game.appid, {})
    ac = gamedb.anticheat_db().get(game.appid)
    native = gamedb.is_native(game.appid)
    findings: list[tuple[Status, str]] = []
    lines: list[str] = []

    # --- чем запускается ---
    tool = mapping.get(game.appid)
    if tool:
        lines.append(t("games.runs.forced", tool=tool))
        if not _tool_is_known(tool, installed_tools):
            findings.append((Status.FAIL, t("games.runs.tool_missing", tool=tool)))
    elif native:
        lines.append(t("games.runs.native"))
    else:
        default = mapping.get("0")
        lines.append(t("games.runs.default", tool=default) if default else t("games.runs.default_steam"))
        if default and not _tool_is_known(default, installed_tools):
            findings.append((Status.FAIL, t("games.runs.tool_missing", tool=default)))

    # --- параметры запуска ---
    opts = options.get(game.appid)
    if opts:
        lines.append(t("games.launch.value", opts=opts))
        findings += analyze_launch_options(opts)
        if native and not tool and re.search(r"\b(PROTON|DXVK|VKD3D|WINE)[A-Z_]*=", opts):
            findings.append((Status.WARN, t("games.launch.proton_vars_native")))

    # --- античит ---
    note_text = (note.get("notes") or {}).get(current_language())
    if note.get("online_broken"):
        findings.append((Status.WARN, note_text or t("games.ac.online_broken")))
        note_text = None  # уже показали как проблему
    else:
        ac_problems, ac_lines = _ac_findings(ac)
        findings += ac_problems
        lines += ac_lines

    # --- требования к системе ---
    need = note.get("min_max_map_count")
    if need and max_map_count is not None and max_map_count < need:
        findings.append((Status.WARN, t("games.need_max_map_count", need=need, have=max_map_count)))

    # --- заметки из базы ---
    if note_text:
        lines.append(note_text)

    # --- база знаний ProtonDB (скачивается отдельно, см. gtux/knowledge.py) ---
    tier = knowledge.tier_for(game.appid)
    if tier and tier.get("tier"):
        lines.append(t("games.tier", tier=tier["tier"], total=tier.get("total") or 0))
    if profile is not None:
        current = parse(opts) if opts else None
        # аргументы игры (например -nobattleye) без пояснений вводят в заблуждение — они только в окне
        tips = [tip.text for tip in knowledge.tips_for(game.appid, profile)
                if not tip.missing_tool and not tip.token.startswith("arg:")
                and not (current and merge(current, tip.as_parsed()) == current)]
        if tips:
            lines.append(t("games.tips", tips=", ".join(tips)))
        pick = knowledge.proton_for(game.appid, profile)
        if pick and pick.broken:
            lines.append(t("games.rec.broken", works=sum(s.works for s in pick.stats),
                           total=sum(s.reports for s in pick.stats)))
        elif pick and pick.best:
            lines.append(t("games.rec", name=t(f"rec.variant.{pick.best.variant}"),
                           works=pick.best.works, total=pick.best.reports))

    status = max((s for s, _ in findings), key=SEVERITY.index, default=Status.OK)
    hint = "\n".join(h for _, h in findings)
    if status != Status.OK:
        hint += "\n" + t("games.protondb", appid=game.appid)
    return {"status": status, "value": "\n".join(lines), "hint": hint}


@check("list")
def check_games(ctx: Context):
    if not ctx.steam_libraries:
        return []
    games = gamedb.installed_games([lib for lib in ctx.steam_libraries if lib.exists()])
    if not games:
        return result(GROUP, "list", Status.OK, value=t("games.none"))
    mapping, options = {}, {}
    for _, root in ctx.steam_roots:
        mapping.update(gamedb.compat_mapping(root))
        options.update(gamedb.launch_options(root))
    installed_tools = installed_tool_names(ctx)
    raw = read_text("/proc/sys/vm/max_map_count")
    max_map_count = int(raw) if raw and raw.isdigit() else None
    profile = knowledge.profile_from(ctx) if knowledge.load() else None

    results = []
    for game in games:
        verdict = assess_game(game, mapping=mapping, options=options,
                              installed_tools=installed_tools, max_map_count=max_map_count, profile=profile)
        results.append(result(GROUP, f"app.{game.appid}", title=game.name, **verdict))
    return results


def _ac_findings(ac: dict | None) -> tuple[list[tuple[Status, str]], list[str]]:
    """(проблемы, строки для показа) по записи AreWeAntiCheatYet."""
    if not ac or ac.get("status") not in ANTICHEAT:
        return [], []
    status, key = ANTICHEAT[ac["status"]]
    text = t(key, anticheats=", ".join(ac.get("anticheats") or []) or "?")
    return ([], [text]) if status == Status.OK else ([(status, text)], [])


def assess_external(game: launchers.ExternalGame, mounts: list[disks.Mount] | None) -> dict:
    findings: list[tuple[Status, str]] = []
    lines: list[str] = []

    if game.install_path is not None and not game.install_path.exists():
        findings.append((Status.FAIL, t("games.ext.no_install", path=game.install_path)))
    if game.windows:
        lines.append(t("games.ext.runner", runner=game.runner or t("games.ext.runner_default")))
        if game.runner_found is False:
            findings.append((Status.FAIL, t("games.ext.runner_missing", runner=game.runner)))
    else:
        lines.append(t("games.runs.native"))

    # префикс Wine на NTFS/exFAT — та же беда, что и у Steam
    if game.prefix and mounts:
        target = game.prefix if game.prefix.exists() else game.prefix.parent
        m = disks.find_mount(target.resolve(), mounts) if target.exists() else None
        if m and disks.real_fstype(m) in disks.NTFS_TYPES | disks.FAT_TYPES:
            findings.append((Status.WARN, t("games.ext.prefix_fs", fs=disks.real_fstype(m))))

    for w in game.wrappers:
        if w in WRAPPERS and not which(w):
            findings.append((Status.FAIL, t("games.launch.missing_tool", tool=w)))
    if game.env:
        lines.append(t("games.ext.env", env=" ".join(f"{k}={v}" for k, v in game.env.items())))
        findings += env_findings(game.env)

    ac_problems, ac_lines = _ac_findings(gamedb.anticheat_by_name(game.name))
    findings += ac_problems
    lines += ac_lines

    status = max((s for s, _ in findings), key=SEVERITY.index, default=Status.OK)
    return {"status": status, "value": "\n".join(lines), "hint": "\n".join(h for _, h in findings)}


@check("other")
def check_other_launchers(ctx: Context):
    games = launchers.all_games()
    if not games:
        return []
    text = read_text("/proc/self/mounts")
    mounts = disks.parse_mounts(text) if text else None
    return [result(GROUP, f"ext.{g.source}.{g.id}", title=t("games.ext.title", name=g.name, source=g.source),
                   **assess_external(g, mounts))
            for g in sorted(games, key=lambda g: (g.source, g.name.lower()))]


CHECKS = [check_games, check_other_launchers]
