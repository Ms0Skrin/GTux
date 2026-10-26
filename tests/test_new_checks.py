import unittest
from pathlib import Path
from unittest import mock

from doctor.checks import gpu, hardware, steam, tuning
from doctor.models import GPU, Context, Status
from doctor.system import CmdResult


class MemoryTest(unittest.TestCase):
    def run_with(self, meminfo, swaps=""):
        files = {"/proc/meminfo": meminfo, "/proc/swaps": swaps}
        with mock.patch.object(hardware, "read_text", lambda p: files.get(str(p))):
            return hardware.check_memory(Context())

    def test_ok(self):
        r = self.run_with("MemTotal: 32689904 kB\nSwapTotal: 32689148 kB\n", "/dev/zram0 partition")
        self.assertEqual(r.status, Status.OK)
        self.assertIn("zram", r.value)

    def test_8gb_machine_is_not_low(self):
        # реальная машина с 8 ГБ показывает ~7.6 ГиБ
        r = self.run_with("MemTotal: 7990000 kB\nSwapTotal: 4000000 kB\n")
        self.assertEqual(r.status, Status.OK)

    def test_no_swap(self):
        r = self.run_with("MemTotal: 16000000 kB\nSwapTotal: 0 kB\n")
        self.assertEqual(r.status, Status.WARN)


class AudioTest(unittest.TestCase):
    def check(self, procs):
        with mock.patch.object(hardware, "running_processes", lambda: set(procs)):
            return hardware.check_audio(Context()).status

    def test_variants(self):
        self.assertEqual(self.check({"pipewire", "pipewire-pulse", "wireplumber"}), Status.OK)
        self.assertEqual(self.check({"pipewire", "wireplumber"}), Status.FAIL)
        self.assertEqual(self.check({"pulseaudio"}), Status.OK)
        self.assertEqual(self.check(set()), Status.WARN)


class FlatpakAccessTest(unittest.TestCase):
    def test_path_allowed(self):
        home = Path("/home/u")
        e = ["xdg-download", "~/.steam", "/mnt/games:ro", "!/mnt/secret"]
        self.assertTrue(steam.path_allowed(Path("/mnt/games/SteamLibrary"), e, home))
        self.assertTrue(steam.path_allowed(Path("/home/u/.steam/x"), e, home))
        self.assertFalse(steam.path_allowed(Path("/mnt/secret/lib"), e, home))
        self.assertFalse(steam.path_allowed(Path("/mnt/other"), e, home))
        self.assertTrue(steam.path_allowed(Path("/mnt/other"), ["host"], home))
        self.assertFalse(steam.path_allowed(Path("/mnt/other"), ["host-os"], home))

    def test_blocked_library(self):
        perms = "[Context]\nfilesystems=xdg-download;~/.steam;\n"
        ctx = Context(steam_roots=[("flatpak", steam.HOME / ".var/app" / steam.FLATPAK_ID / "data/Steam")],
                      steam_libraries=[Path("/mnt/games/SteamLibrary")])
        with mock.patch.object(steam, "run", lambda cmd: CmdResult(0, perms, "")), \
                mock.patch.object(steam, "which", lambda n: "/usr/bin/flatpak"):
            r = steam.check_flatpak_access(ctx)
        self.assertEqual(r.status, Status.FAIL)
        self.assertIn("flatpak override --user --filesystem=/mnt/games/SteamLibrary", r.fix)


class KernelKnobsTest(unittest.TestCase):
    def test_split_lock(self):
        for raw, expected in (("1", Status.WARN), ("0", Status.OK)):
            with mock.patch.object(tuning, "read_text", lambda p, raw=raw: raw):
                self.assertEqual(tuning.check_split_lock(Context()).status, expected)
        with mock.patch.object(tuning, "read_text", lambda p: None):
            self.assertEqual(tuning.check_split_lock(Context()), [])

    def test_modeset_on_wayland(self):
        ctx = Context(gpus=[GPU("nvidia", "0x10de", "RTX", "nvidia", "x")])
        with mock.patch.object(gpu, "read_text", lambda p: "N"), \
                mock.patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland"}):
            self.assertEqual(gpu.check_modeset(ctx).status, Status.FAIL)
        self.assertEqual(gpu.check_modeset(Context()), [])  # нет NVIDIA — нечего показывать


if __name__ == "__main__":
    unittest.main()
