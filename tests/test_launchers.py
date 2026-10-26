"""Heroic / Lutris / Faugus на поддельных файлах в формате из исходников лаунчеров."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gtux import launchers
from gtux.checks import disks, games
from gtux.models import Status


class LauncherFixtures(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.game_dir = self.home / "Games" / "Hades"
        self.game_dir.mkdir(parents=True)
        self.wine = self.home / "wine" / "bin" / "wine"
        self.wine.parent.mkdir(parents=True)
        self.wine.touch()

    def write(self, rel, data):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data if isinstance(data, str) else json.dumps(data))
        return p

    # ---------- Heroic ----------
    def heroic(self):
        root = self.home / ".config/heroic"
        self.write(".config/heroic/legendaryConfig/legendary/installed.json", {
            "Fortnite": {"app_name": "Fortnite", "title": "Fortnite", "install_path": str(self.game_dir),
                         "platform": "Windows", "is_dlc": False},
            "Gone": {"app_name": "Gone", "title": "Удалённая игра", "install_path": "/nope/gone",
                     "platform": "Windows"},
        })
        self.write(".config/heroic/GamesConfig/Fortnite.json", {"Fortnite": {
            "wineVersion": {"bin": str(self.wine), "name": "GE-Proton9-20", "type": "proton"},
            "winePrefix": str(self.home / "Prefixes/fn"),
            "enviromentOptions": [{"key": "WINE_CPU_TOPOLOGY", "value": "4:0,1"}],
            "wrapperOptions": [], "useGameMode": True, "showMangohud": False}})
        self.write(".config/heroic/GamesConfig/Gone.json", {"Gone": {
            "wineVersion": {"bin": "/nope/wine", "name": "Wine-GE-8", "type": "wine"}}})
        self.write(".config/heroic/gog_store/installed.json", {"installed": [
            {"appName": "1207658924", "install_path": str(self.game_dir), "platform": "linux"}]})
        self.write(".config/heroic/store_cache/gog_library.json", {"games": [
            {"app_name": "1207658924", "title": "Hades"}]})
        with mock.patch.object(launchers, "HEROIC_DIRS", [root]):
            return {g.name: g for g in launchers.heroic_games()}

    def test_heroic_parsed(self):
        g = self.heroic()
        self.assertEqual(set(g), {"Fortnite", "Удалённая игра", "Hades"})
        fn = g["Fortnite"]
        self.assertEqual((fn.runner, fn.runner_found, fn.wrappers), ("GE-Proton9-20", True, ["gamemoderun"]))
        self.assertEqual(fn.env, {"WINE_CPU_TOPOLOGY": "4:0,1"})
        self.assertFalse(g["Hades"].windows)
        self.assertEqual(g["Hades"].source, "Heroic (GOG)")

    def test_heroic_verdicts(self):
        g = self.heroic()
        with mock.patch.object(games, "which", lambda n: None):
            fn = games.assess_external(g["Fortnite"], None)
        self.assertEqual(fn["status"], Status.FAIL)            # gamemoderun нет в системе
        self.assertIn("WINE_CPU_TOPOLOGY", fn["hint"])          # 4:0,1 — неверный счёт
        self.assertIn("Easy Anti-Cheat", fn["hint"])            # Fortnite — Denied
        gone = games.assess_external(g["Удалённая игра"], None)
        self.assertEqual(gone["status"], Status.FAIL)
        self.assertIn("/nope/gone", gone["hint"])
        self.assertEqual(games.assess_external(g["Hades"], None)["status"], Status.OK)

    # ---------- Lutris ----------
    def test_lutris(self):
        data = self.home / ".local/share/lutris"
        data.mkdir(parents=True)
        con = sqlite3.connect(data / "pga.db")
        con.execute("CREATE TABLE games (slug, name, runner, directory, configpath, installed)")
        con.executemany("INSERT INTO games VALUES (?,?,?,?,?,?)", [
            ("witcher-3", "The Witcher 3", "wine", str(self.game_dir), "witcher-3-123", 1),
            ("old", "Old", "wine", "", "old-1", 0),  # не установлена — пропускаем
        ])
        con.commit()
        con.close()
        (data / "runners/wine/lutris-GE-Proton8-26-x86_64").mkdir(parents=True)
        self.write(".local/share/lutris/games/witcher-3-123.yml", """game:
  exe: /games/witcher3.exe
  prefix: /games/prefix
system:
  gamemode: true
  env:
    DXVK_ASYNC: '1'
wine:
  version: lutris-GE-Proton7-1-x86_64
""")
        with mock.patch.object(launchers, "LUTRIS_DATA_DIRS", [data]), \
                mock.patch.object(launchers, "LUTRIS_CONFIG_DIRS", []):
            found = launchers.lutris_games()
        self.assertEqual(len(found), 1)
        w = found[0]
        self.assertEqual((w.runner, w.runner_found), ("lutris-GE-Proton7-1-x86_64", False))
        self.assertEqual(w.env, {"DXVK_ASYNC": "1"})
        self.assertEqual(w.wrappers, ["gamemoderun"])
        self.assertEqual(games.assess_external(w, None)["status"], Status.FAIL)  # wine удалён

    # ---------- Faugus ----------
    def test_faugus(self):
        (self.game_dir / "cp.exe").touch()
        win = self.home / "win"
        (win / "prefix").mkdir(parents=True)
        f = self.write(".local/share/faugus-launcher/games.json", [
            {"gameid": "cyberpunk", "title": "Cyberpunk 2077", "path": str(self.game_dir / "cp.exe"),
             "prefix": str(win / "prefix"), "launch_arguments": "PROTON_USE_WINED3D=1 DXVK_HUD=fps",
             "mangohud": True, "gamemode": False, "runner": "GE-Proton"},
            {"gameid": "s", "title": "Steam shortcut", "runner": "Steam"},
        ])
        with mock.patch.object(launchers, "FAUGUS_GAMES", [f]):
            found = launchers.faugus_games()
        self.assertEqual([g.name for g in found], ["Cyberpunk 2077"])
        cp = found[0]
        self.assertEqual(cp.wrappers, ["mangohud"])
        self.assertEqual(cp.env["PROTON_USE_WINED3D"], "1")
        mounts = disks.parse_mounts(f"/dev/a / ext4 rw 0 0\n/dev/b {win} ntfs3 rw 0 0\n")
        with mock.patch.object(games, "which", lambda n: "/usr/bin/" + n):
            v = games.assess_external(cp, mounts)
        self.assertEqual(v["status"], Status.WARN)
        self.assertIn("ntfs3", v["hint"])
        self.assertIn("PROTON_USE_WINED3D", v["hint"])

    def test_broken_files_are_skipped(self):
        f = self.write(".local/share/faugus-launcher/games.json", "{не json")
        with mock.patch.object(launchers, "FAUGUS_GAMES", [f]):
            self.assertEqual(launchers.faugus_games(), [])


class YamlTest(unittest.TestCase):
    def test_nested(self):
        y = launchers.parse_simple_yaml("game:\n  exe: a.exe\nsystem:\n  env:\n    A: '1'\n  gamemode: true\n")
        self.assertEqual(y["system"]["env"], {"A": "1"})
        self.assertEqual(y["system"]["gamemode"], "true")


if __name__ == "__main__":
    unittest.main()
