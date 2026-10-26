"""apt/dnf без настоящих Debian и Fedora: подменяем вывод dpkg-query и rpm."""

import unittest
from unittest import mock

from gtux import packages, pkgnames
from gtux.checks import multilib
from gtux.models import GPU, Context, Status
from gtux.system import CmdResult


def fake_run(installed: dict[str, str], foreign=""):
    def run(cmd, timeout=15):
        if cmd[:2] == ["dpkg", "--print-architecture"]:
            return CmdResult(0, "amd64\n", "")
        if cmd[:2] == ["dpkg", "--print-foreign-architectures"]:
            return CmdResult(0, foreign, "")
        if cmd[0] == "dpkg-query":
            name = cmd[-1]
            if name in installed:
                return CmdResult(0, f"ii  {installed[name]}\n", "")
            return CmdResult(1, "", f"dpkg-query: no packages found matching {name}\n")
        if cmd[0] == "rpm":
            name = cmd[-1]
            if name in installed:
                return CmdResult(0, installed[name] + "\n", "")
            return CmdResult(1, f"package {name} is not installed\n", "")
        raise AssertionError(cmd)
    return run


class AptTest(unittest.TestCase):
    def test_native_arch_is_explicit(self):
        with mock.patch.object(packages, "run", fake_run({"libvulkan1:amd64": "1.3.280-1",
                                                          "libvulkan1:i386": "1.3.280-1"})):
            v = packages.Apt().installed_versions(["libvulkan1", "libvulkan1:i386", "steam-installer"])
        self.assertEqual(v, {"libvulkan1": "1.3.280-1", "libvulkan1:i386": "1.3.280-1",
                             "steam-installer": None})

    def test_removed_but_config_left_is_not_installed(self):
        def run(cmd, timeout=15):
            if cmd[:2] == ["dpkg", "--print-architecture"]:
                return CmdResult(0, "amd64\n", "")
            return CmdResult(0, "rc  1.0-1\n", "")
        with mock.patch.object(packages, "run", run):
            self.assertIsNone(packages.Apt().installed_versions(["gamemode"])["gamemode"])

    def test_commands(self):
        apt = packages.Apt()
        self.assertEqual(apt.install_command(["a", "b:i386"]), "sudo apt install a b:i386")
        self.assertTrue(apt.is_32bit("b:i386"))


class DnfTest(unittest.TestCase):
    def test_installed(self):
        with mock.patch.object(packages, "run", fake_run({"vulkan-loader.i686": "1.4.304.0-1.fc42"})):
            v = packages.Dnf().installed_versions(["vulkan-loader.i686", "steam"])
        self.assertEqual(v, {"vulkan-loader.i686": "1.4.304.0-1.fc42", "steam": None})


class NamesTest(unittest.TestCase):
    def test_ubuntu_nvidia_branch(self):
        self.assertEqual(pkgnames.resolve("lib32_nvidia", "ubuntu", nvidia_branch="550"),
                         ["libnvidia-gl-550:i386"])
        self.assertIsNone(pkgnames.resolve("lib32_nvidia", "ubuntu"))  # ветка неизвестна

    def test_unknown_family(self):
        self.assertIsNone(pkgnames.resolve("steam", None))
        self.assertIsNone(pkgnames.resolve("lib32_gamemode", "fedora"))

    def test_every_component_has_arch(self):
        for name, families in pkgnames.COMPONENTS.items():
            self.assertIn("arch", families, name)


class Lib32Scenarios(unittest.TestCase):
    def run_group(self, pm, installed, foreign=""):
        ctx = Context(package_manager=pm, gpus=[GPU("amd", "0x1002", "RX 6600", "amdgpu", "x")])
        with mock.patch.object(packages, "run", fake_run(installed, foreign)):
            return [f(ctx) for f in multilib.CHECKS]

    def test_debian_without_i386(self):
        repo, pkgs, _ = self.run_group(packages.Apt(), {})
        self.assertEqual(repo.status, Status.FAIL)
        self.assertIn("dpkg --add-architecture i386", repo.fix)
        self.assertEqual(pkgs.status, Status.FAIL)
        self.assertIn("mesa-vulkan-drivers:i386", pkgs.packages)

    def test_fedora_all_installed(self):
        have = {p: "1-1" for p in ("vulkan-loader.i686", "mesa-dri-drivers.i686", "mesa-vulkan-drivers.i686")}
        repo, pkgs, nv = self.run_group(packages.Dnf(), have)
        self.assertEqual((repo.status, pkgs.status), (Status.OK, Status.OK))
        self.assertEqual(nv, [])  # сверка версий NVIDIA — только на Arch


if __name__ == "__main__":
    unittest.main()


class UnavailableTest(unittest.TestCase):
    def test_apt_candidates_and_lists(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        out = ("steam-installer:\n  Installed: (none)\n  Candidate: (none)\n"
               "gamemode:\n  Installed: (none)\n  Candidate: 1.8.2-2\n")
        with tempfile.TemporaryDirectory() as lists, \
                mock.patch.object(packages, "APT_LISTS", lists), \
                mock.patch.object(packages, "run", return_value=CmdResult(0, out, "")):
            self.assertIsNone(packages.Apt().unavailable(["gamemode"]))  # списков нет — не судим
            (Path(lists) / "deb.debian.org_debian_dists_trixie_main_binary-amd64_Packages").write_text("")
            # lutris apt вообще не знает (нет в выводе), steam-installer без кандидата, :i386 — по 64-битному имени
            self.assertEqual(packages.Apt().unavailable(["gamemode", "steam-installer", "lutris", "gamemode:i386"]),
                             ["steam-installer", "lutris"])

    def test_pacman_not_found(self):
        from unittest import mock
        from gtux.system import CmdResult
        err = "error: package 'heroic-games-launcher' was not found\n"
        with mock.patch.object(packages, "run", return_value=CmdResult(1, "", err)):
            self.assertEqual(packages.Pacman().unavailable(["lutris", "heroic-games-launcher"]),
                             ["heroic-games-launcher"])
