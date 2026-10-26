import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gtux.checks import logs
from gtux.models import Context, Status

SAMPLE = """\
0024:err:module:import_dll Library MSVCP140.dll (which is needed by L"Z:\\\\games\\\\game.exe") not found
0024:err:module:import_dll Library VCRUNTIME140_1.dll (which is needed by L"Z:\\\\games\\\\game.exe") not found
err:   DxvkSubmissionQueue: Command submission failed: VK_ERROR_DEVICE_LOST
"""


class AnalyzeTest(unittest.TestCase):
    def test_missing_dll_and_device_lost(self):
        f = logs.analyze(SAMPLE, "275850")
        statuses = [s for s, _, _ in f]
        self.assertEqual(statuses, [Status.FAIL, Status.WARN])
        self.assertEqual(f[0][2], "protontricks 275850 vcrun2022")
        self.assertIn("MSVCP140.dll", f[0][1])

    def test_unknown_dll_has_no_fix(self):
        f = logs.analyze('err:module:import_dll Library foo.dll (which is needed by L"x") not found', "1")
        self.assertIsNone(f[0][2])

    def test_clean(self):
        self.assertEqual(logs.analyze("fixme:ntdll:something harmless\n", "1"), [])

    def test_broken_prefix(self):
        f = logs.analyze('wine: could not load L"C:\\\\windows\\\\system32\\\\kernel32.dll", status c0000135', "1")
        self.assertEqual(f[0][0], Status.FAIL)


class CheckTest(unittest.TestCase):
    def test_reads_only_tail_and_lists_logs(self):
        d = Path(tempfile.mkdtemp())
        (d / "steam-42.log").write_text("x" * 100 + "\nUnhandled exception: page fault\n")
        with mock.patch.dict(os.environ, {"PROTON_LOG_DIR": str(d)}):
            res = logs.check_logs(Context())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, Status.WARN)
        self.assertEqual(logs.read_tail(d / "steam-42.log", 10), "age fault\n")

    def test_no_logs(self):
        with mock.patch.dict(os.environ, {"PROTON_LOG_DIR": tempfile.mkdtemp()}):
            self.assertEqual(logs.check_logs(Context()).status, Status.OK)


if __name__ == "__main__":
    unittest.main()
