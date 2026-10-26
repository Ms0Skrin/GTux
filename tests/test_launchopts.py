import unittest
from unittest import mock

from doctor.checks import games
from doctor.launchopts import LaunchConfig, build


class BuildTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build(LaunchConfig()), "%command%")

    def test_full(self):
        cfg = LaunchConfig(gamemode=True, mangohud=True, dxvk_hud=True, cpu_cores=4, game_args="-novid")
        self.assertEqual(build(cfg),
                         "DXVK_HUD=fps WINE_CPU_TOPOLOGY=4:0,1,2,3 gamemoderun mangohud %command% -novid")

    def test_gamescope_uses_mangoapp(self):
        cfg = LaunchConfig(gamescope=True, gamescope_width=2560, gamescope_height=1440,
                           mangohud=True, gamemode=True)
        self.assertEqual(build(cfg), "gamescope -W 2560 -H 1440 -f --mangoapp -- gamemoderun %command%")

    def test_bad_quotes(self):
        with self.assertRaises(ValueError):
            build(LaunchConfig(game_args='-name "abc'))

    def test_result_passes_our_own_checker(self):
        cfg = LaunchConfig(gamemode=True, mangohud=True, no_fsync=True, cpu_cores=8)
        with mock.patch.object(games, "which", lambda n: "/usr/bin/" + n):
            self.assertEqual(games.analyze_launch_options(build(cfg), cpu_count=16), [])


if __name__ == "__main__":
    unittest.main()
