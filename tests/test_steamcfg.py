import tempfile
import unittest
from pathlib import Path

from gtux import steamcfg

CONFIG = '''"UserLocalConfigStore"
{
\t"Software"
\t{
\t\t"Valve"
\t\t{
\t\t\t"Steam"
\t\t\t{
\t\t\t\t"apps"
\t\t\t\t{
\t\t\t\t\t"730"
\t\t\t\t\t{
\t\t\t\t\t\t"LastPlayed"\t\t"1790502709"
\t\t\t\t\t\t"LaunchOptions"\t\t"gamemoderun %command%"
\t\t\t\t\t}
\t\t\t\t\t"240"
\t\t\t\t\t{
\t\t\t\t\t\t"Playtime"\t\t"613"
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
'''


class EditTest(unittest.TestCase):
    def test_replace_keeps_rest(self):
        new = steamcfg.set_launch_options(CONFIG, "730", 'mangohud "a b" %command%')
        self.assertEqual(steamcfg.read_launch_options(new, "730"), 'mangohud "a b" %command%')
        self.assertEqual(new.replace('"mangohud \\"a b\\" %command%"', '"gamemoderun %command%"'), CONFIG)

    def test_add_to_existing_game(self):
        new = steamcfg.set_launch_options(CONFIG, "240", "PROTON_NO_ESYNC=1 %command%")
        self.assertIn('\t\t\t\t\t\t"LaunchOptions"\t\t"PROTON_NO_ESYNC=1 %command%"\n\t\t\t\t\t}', new)
        self.assertEqual(steamcfg.read_launch_options(new, "730"), "gamemoderun %command%")

    def test_add_new_game_and_remove(self):
        new = steamcfg.set_launch_options(CONFIG, "999", "%command% -novid")
        self.assertEqual(steamcfg.read_launch_options(new, "999"), "%command% -novid")
        gone = steamcfg.set_launch_options(new, "730", None)
        self.assertIsNone(steamcfg.read_launch_options(gone, "730"))
        self.assertIn('"LastPlayed"', gone)

    def test_write_backup_and_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "userdata/1/config/localconfig.vdf"
            config.parent.mkdir(parents=True)
            config.write_text(CONFIG)
            backups = Path(tmp) / "backups"
            old = steamcfg.write(config, "730", "%command%", directory=backups, check_running=False)
            self.assertEqual(old, "gamemoderun %command%")
            self.assertEqual(steamcfg.read_launch_options(config.read_text(), "730"), "%command%")
            self.assertEqual(len(list(backups.glob("localconfig-1-*.vdf"))), 1)
            self.assertEqual(steamcfg.last_change("730", backups)["old"], "gamemoderun %command%")
            self.assertEqual(steamcfg.localconfig_path(Path(tmp)), config)

    def test_broken_file_is_not_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "localconfig.vdf"
            config.write_text('"a" {')
            with self.assertRaises(steamcfg.SteamConfigError):
                steamcfg.write(config, "1", "%command%", directory=Path(tmp) / "b", check_running=False)
            self.assertEqual(config.read_text(), '"a" {')


if __name__ == "__main__":
    unittest.main()


COMPAT = '''"InstallConfigStore"
{
\t"Software"
\t{
\t\t"Valve"
\t\t{
\t\t\t"Steam"
\t\t\t{
\t\t\t\t"CompatToolMapping"
\t\t\t\t{
\t\t\t\t\t"0"
\t\t\t\t\t{
\t\t\t\t\t\t"name"\t\t"proton-cachyos-slr"
\t\t\t\t\t\t"config"\t\t""
\t\t\t\t\t\t"priority"\t\t"75"
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\t"Tools"
\t\t\t\t{
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
'''


class CompatTest(unittest.TestCase):
    def test_add_replace_remove_byte_exact(self):
        t1 = steamcfg.set_compat_tool(COMPAT, "1771300", "proton_11")
        self.assertEqual(steamcfg.read_compat_tool(t1, "1771300"), "proton_11")
        self.assertIn('\t\t\t\t\t\t"priority"\t\t"250"\n', t1)
        self.assertEqual(steamcfg.read_compat_tool(t1, "0"), "proton-cachyos-slr")  # «по умолчанию» не тронут
        t2 = steamcfg.set_compat_tool(t1, "1771300", "GE-Proton11-11")
        self.assertEqual(steamcfg.read_compat_tool(t2, "1771300"), "GE-Proton11-11")
        self.assertEqual(steamcfg.set_compat_tool(t2, "1771300", None), COMPAT)
        self.assertEqual(steamcfg.set_compat_tool(COMPAT, "5", None), COMPAT)

    def test_write_with_backup_journal_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.vdf"
            config.write_text(COMPAT)
            backups = Path(tmp) / "backups"
            old = steamcfg.write_compat(config, "1771300", "proton_11", directory=backups, check_running=False)
            self.assertIsNone(old)
            self.assertEqual(steamcfg.read_compat_tool(config.read_text(), "1771300"), "proton_11")
            last = steamcfg.last_change("1771300", backups, kind="compat")
            self.assertEqual((last["old"], last["new"]), (None, "proton_11"))
            self.assertIsNone(steamcfg.last_change("1771300", backups))  # параметры запуска не путаются со сборкой
            self.assertEqual(Path(last["backup"]).read_text(), COMPAT)
            steamcfg.write_compat(config, "1771300", last["old"], directory=backups, check_running=False, undo=True)
            self.assertEqual(config.read_text(), COMPAT)
