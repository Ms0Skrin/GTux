import tempfile
import unittest
from pathlib import Path
from unittest import mock

from doctor import gamedb
from doctor.checks import games
from doctor.models import Status


def statuses(opts, **kw):
    return [s for s, _ in games.analyze_launch_options(opts, **kw)]


class LaunchOptionsTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(games, "which", lambda name: f"/usr/bin/{name}")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_good(self):
        self.assertEqual(statuses("gamemoderun mangohud %command%"), [])
        self.assertEqual(statuses("WINE_CPU_TOPOLOGY=4:0,1,2,3 %command% -novid", cpu_count=8), [])

    def test_missing_command(self):
        self.assertEqual(statuses("PROTON_LOG=1"), [Status.FAIL])
        self.assertEqual(statuses("-novid -high"), [])  # просто аргументы игре — это нормально

    def test_topology(self):
        self.assertEqual(statuses("WINE_CPU_TOPOLOGY=10:20 %command%", cpu_count=40), [Status.WARN])
        self.assertEqual(statuses("WINE_CPU_TOPOLOGY=2:0,99 %command%", cpu_count=8), [Status.WARN])

    def test_wined3d(self):
        self.assertEqual(statuses("PROTON_USE_WINED3D=1 %command%"), [Status.WARN])
        self.assertEqual(statuses("PROTON_USE_WINED3D=0 %command%"), [])

    def test_missing_wrapper(self):
        with mock.patch.object(games, "which", lambda name: None):
            self.assertEqual(statuses("mangohud %command%"), [Status.FAIL])

    def test_bad_quotes(self):
        self.assertEqual(statuses('FOO="bar %command%'), [Status.WARN])


class AssessTest(unittest.TestCase):
    def assess(self, appid, **kw):
        args = dict(mapping={}, options={}, installed_tools=set(), max_map_count=1048576)
        args.update(kw)
        return games.assess_game(gamedb.Game(appid, "Game", Path("/x")), **args)

    def test_removed_proton_build(self):
        v = self.assess("123", mapping={"123": "ge-proton8-1"})
        self.assertEqual(v["status"], Status.FAIL)
        self.assertEqual(self.assess("123", mapping={"123": "proton_experimental"})["status"], Status.OK)

    def test_proton_vars_on_native_game(self):
        v = self.assess("227300", options={"227300": "PROTON_NO_ESYNC=1 %command%"})
        self.assertEqual(v["status"], Status.WARN)

    def test_max_map_count_requirement(self):
        self.assertEqual(self.assess("221100", max_map_count=65530)["status"], Status.WARN)

    def test_denied_anticheat(self):
        v = self.assess("2073620")  # Arena Breakout: Infinite — Denied в снимке AreWeAntiCheatYet
        self.assertEqual(v["status"], Status.WARN)
        self.assertIn("protondb.com/app/2073620", v["hint"])


class SteamFilesTest(unittest.TestCase):
    def test_installed_games_skip_tools(self):
        lib = Path(tempfile.mkdtemp())
        (lib / "steamapps").mkdir()
        for appid, name in [("1", "Real Game"), ("2", "Proton 9.0"), ("3", "Steam Linux Runtime 3.0 (sniper)")]:
            (lib / "steamapps" / f"appmanifest_{appid}.acf").write_text(
                f'"AppState" {{ "appid" "{appid}" "name" "{name}" }}')
        (lib / "steamapps" / "appmanifest_9.acf").write_text("битый {")
        self.assertEqual([g.name for g in gamedb.installed_games([lib])], ["Real Game"])


class DataIntegrityTest(unittest.TestCase):
    def test_every_note_has_source_and_ru(self):
        for appid, entry in gamedb.notes_db().items():
            self.assertTrue(appid.isdigit(), appid)
            self.assertTrue(entry.get("sources"), f"{appid}: нет источника")
            if "notes" in entry:
                self.assertIn("ru", entry["notes"], appid)

    def test_anticheat_snapshot_loaded(self):
        self.assertGreater(len(gamedb.anticheat_db()), 100)


if __name__ == "__main__":
    unittest.main()
