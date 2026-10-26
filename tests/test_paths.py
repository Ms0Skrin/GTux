import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gtux import paths


class PathsTest(unittest.TestCase):
    def test_old_folder_moves_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "linux-gamer-doctor" / "history"
            old.mkdir(parents=True)
            (old / "1.json").write_text("{}")
            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": tmp}):
                new = paths.state_dir()
                self.assertEqual(new, Path(tmp) / "gtux")
                self.assertTrue((new / "history" / "1.json").is_file())
                self.assertFalse((Path(tmp) / "linux-gamer-doctor").exists())
                # новая папка уже есть — старую (если вдруг появилась снова) не трогаем
                (Path(tmp) / "linux-gamer-doctor").mkdir()
                self.assertEqual(paths.state_dir(), new)
                self.assertTrue((Path(tmp) / "linux-gamer-doctor").is_dir())

    def test_no_old_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": tmp}):
                self.assertEqual(paths.cache_dir(), Path(tmp) / "gtux")
