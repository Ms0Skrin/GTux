import unittest
from unittest import mock

from gtux.checks import games
from gtux.launchopts import LaunchConfig, build


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


class ParseTest(unittest.TestCase):
    def test_roundtrip_and_env_first(self):
        from gtux.launchopts import compose, parse
        self.assertEqual(compose(parse("gamemoderun PROTON_NO_ESYNC=1 %command% -novid")),
                         "PROTON_NO_ESYNC=1 gamemoderun %command% -novid")
        self.assertEqual(compose(parse("-novid -high")), "%command% -novid -high")
        self.assertEqual(compose(parse('WINEDLLOVERRIDES="winmm=n,b" %command%')),
                         "WINEDLLOVERRIDES=winmm=n,b %command%")

    def test_refuses_shell(self):
        from gtux.launchopts import parse
        for bad in ["bash -c 'x' %command%", "%command% %command%", "%command% ; rm -rf ~",
                    "echo hi", "%command% $(id)"]:
            self.assertIsNone(parse(bad), bad)

    def test_merge_and_config_from(self):
        from gtux.launchopts import Parsed, compose, config_from, merge, parse
        base = parse("mangohud PROTON_NO_ESYNC=1 VKD3D_CONFIG=dxr %command% -dx11")
        merged = merge(base, Parsed(env={"PROTON_NO_ESYNC": "1"}, wrappers=["gamemoderun"], args=["-dx11"]))
        self.assertEqual(compose(merged), "PROTON_NO_ESYNC=1 VKD3D_CONFIG=dxr gamemoderun mangohud %command% -dx11")
        cfg, rest = config_from(base)
        self.assertTrue(cfg.mangohud and cfg.no_esync)
        self.assertEqual((rest.env, rest.wrappers, cfg.game_args), ({"VKD3D_CONFIG": "dxr"}, [], "-dx11"))
        # переключатели + остаток дают то же самое (порядок переменных не важен)
        self.assertEqual(merge(rest, parse(build(cfg))), base)
