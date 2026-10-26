import unittest
from pathlib import Path

from gtux import packages, vdf
from gtux.checks import disks, multilib, vulkan


class VDFTest(unittest.TestCase):
    def test_libraryfolders(self):
        text = '''"libraryfolders"
        {
            "0" { "path" "/home/u/.local/share/Steam" "apps" { "228980" "1" } }
            "1" { "path" "/mnt/games/SteamLibrary" }
        }'''
        data = vdf.loads(text)
        self.assertEqual(data["libraryfolders"]["1"]["path"], "/mnt/games/SteamLibrary")

    def test_comments_ignored(self):
        text = '''"compatibilitytools" { "compat_tools" {
            // "display_name" "из комментария"
            "GE" { "display_name" "GE-Proton11-9" } } }'''
        tools = vdf.loads(text)["compatibilitytools"]["compat_tools"]
        self.assertEqual(tools["ge"]["display_name"], "GE-Proton11-9")

    def test_broken(self):
        with self.assertRaises(vdf.VDFError):
            vdf.loads('"a" { "b" "c"')


class SmallParsersTest(unittest.TestCase):
    def test_strip_version(self):
        self.assertEqual(packages.strip_version("3:26.2.4-1"), "26.2.4")
        self.assertEqual(packages.strip_version("615.78.08-2"), "615.78.08")

    def test_multilib(self):
        self.assertTrue(multilib.multilib_enabled("[options]\n[multilib] \nInclude = x"))
        self.assertTrue(multilib.multilib_enabled("[multilib]  # комментарий"))
        self.assertFalse(multilib.multilib_enabled("#[multilib]\n#Include = x"))

    def test_vulkaninfo(self):
        text = ("WARNING: something\nDevices:\n========\nGPU0:\n\tvendorID = 0x10de\n"
                "\tdeviceName = RTX\nGPU1:\n\tdeviceType = PHYSICAL_DEVICE_TYPE_CPU\n")
        devs = vulkan.parse_vulkaninfo_summary(text)
        self.assertEqual(len(devs), 2)
        self.assertEqual(devs[0]["deviceName"], "RTX")

    def test_mounts(self):
        mounts = disks.parse_mounts(
            "/dev/a / ext4 rw 0 0\n/dev/b /mnt/my\\040games ntfs3 rw,windows_names 0 0\n")
        m = disks.find_mount(Path("/mnt/my games/SteamLibrary"), mounts)
        self.assertEqual(m.fstype, "ntfs3")
        self.assertIn("windows_names", m.options)
        self.assertEqual(disks.find_mount(Path("/home/u"), mounts).target, "/")


if __name__ == "__main__":
    unittest.main()
