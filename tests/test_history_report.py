import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from doctor import history, log as doctor_log
from doctor.models import CheckResult, Status
from doctor.output import report


def r(rid, status=Status.OK, value=""):
    return CheckResult(rid, rid.split(".")[0], rid, status, value=value)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_save_load_diff(self):
        history.save([r("distro.kernel", value="6.9"), r("tools.mangohud", Status.WARN), r("games.app.1")], self.dir)
        prev = history.load_latest(self.dir)
        changes = history.diff(prev, [r("distro.kernel", value="7.0"), r("tools.mangohud"), r("games.app.2")])
        kinds = {(c.id, c.kind) for c in changes}
        self.assertEqual(kinds, {("distro.kernel", "value"), ("tools.mangohud", "status"),
                                 ("games.app.2", "added"), ("games.app.1", "removed")})

    def test_untracked_value_change_ignored(self):
        history.save([r("disks.library.0", value="свободно 10 ГБ")], self.dir)
        prev = history.load_latest(self.dir)
        self.assertEqual(history.diff(prev, [r("disks.library.0", value="свободно 9 ГБ")]), [])

    def test_rotation(self):
        with mock.patch.object(history, "MAX_FILES", 3):
            for i in range(5):
                with mock.patch.object(history.time, "strftime", return_value=f"2026-{i}"):
                    history.save([r("a.b")], self.dir)
        self.assertEqual(len(list(self.dir.glob("*.json"))), 3)

    def test_no_previous(self):
        self.assertEqual(history.diff(None, [r("a.b")]), [])


class ReportTest(unittest.TestCase):
    def test_masks_home_and_escapes(self):
        home = str(Path.home())
        md = report.render([r("distro.os", value="Arch"),
                            CheckResult("disks.x", "disks", "Disk", Status.WARN, value=f"{home}/Games | ntfs",
                                        hint="NTFS")])
        self.assertNotIn(home, md)
        self.assertIn("~/Games \\| ntfs", md)
        self.assertIn("⚠️ **Disk**", md)


class LogTest(unittest.TestCase):
    def test_writes_file(self):
        d = tempfile.mkdtemp()
        logger = logging.getLogger("doctor")
        saved = logger.handlers[:]
        logger.handlers.clear()
        try:
            with mock.patch.dict("os.environ", {"XDG_STATE_HOME": d}):
                path = doctor_log.setup()
                logging.getLogger("doctor.test").warning("проверка журнала")
                for h in logger.handlers:
                    h.flush()
                self.assertIn("проверка журнала", path.read_text())
        finally:
            for h in logger.handlers:
                h.close()
            logger.handlers[:] = saved


if __name__ == "__main__":
    unittest.main()
