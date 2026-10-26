"""Сценарии для дисков на временных папках: подменяем /proc/mounts выдуманным текстом."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gtux.checks import disks
from gtux.models import Status


class DiskScenarios(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.lib = self.tmp / "games" / "SteamLibrary"
        (self.lib / "steamapps").mkdir(parents=True)
        self.linux = self.tmp / "home"
        self.linux.mkdir()

    def assess(self, lib_fs, opts="rw", dirty_log=(), compat_on_linux=False, free=500 * 1024**3):
        if compat_on_linux:
            target = self.linux / "compatdata"
            target.mkdir()
            (self.lib / "steamapps" / "compatdata").symlink_to(target)
        mounts = disks.parse_mounts(
            f"/dev/root / ext4 rw 0 0\n"
            f"/dev/sdb1 {self.tmp / 'games'} {lib_fs} {opts} 0 0\n"
            f"/dev/sda2 {self.linux} ext4 rw 0 0\n")
        usage = mock.Mock(free=free)
        with mock.patch.object(disks.shutil, "disk_usage", return_value=usage):
            return disks.assess_library(self.lib, mounts, list(dirty_log))

    def test_ext4_ok(self):
        self.assertEqual(self.assess("ext4")["status"], Status.OK)

    def test_ntfs_warn(self):
        self.assertEqual(self.assess("ntfs3")["status"], Status.WARN)

    def test_ntfs_windows_names_fail(self):
        self.assertEqual(self.assess("ntfs3", "rw,windows_names")["status"], Status.FAIL)

    def test_ntfs_compat_moved_warn(self):
        v = self.assess("ntfs3", "rw,windows_names", compat_on_linux=True)
        self.assertEqual(v["status"], Status.WARN)
        self.assertIn("ext4", v["value"])

    def test_exfat_fail(self):
        self.assertEqual(self.assess("exfat")["status"], Status.FAIL)

    def test_readonly_fail(self):
        self.assertEqual(self.assess("ext4", "ro")["status"], Status.FAIL)

    def test_noexec_fail(self):
        self.assertEqual(self.assess("ext4", "rw,noexec")["status"], Status.FAIL)

    def test_dirty_fail(self):
        v = self.assess("ntfs3", dirty_log=["ntfs3: sdb1: volume is dirty"], compat_on_linux=True)
        self.assertEqual(v["status"], Status.FAIL)

    def test_unreadable_kernel_log_is_reported(self):
        mounts = disks.parse_mounts(f"/dev/sdb1 {self.tmp / 'games'} ntfs3 rw 0 0\n")
        with mock.patch.object(disks.shutil, "disk_usage", return_value=mock.Mock(free=10**12)):
            v = disks.assess_library(self.lib, mounts, None)  # None = журнал ядра недоступен
        self.assertIn("Журнал ядра недоступен", v["hint"])

    def test_low_space_warn(self):
        self.assertEqual(self.assess("ext4", free=5 * 1024**3)["status"], Status.WARN)


if __name__ == "__main__":
    unittest.main()
