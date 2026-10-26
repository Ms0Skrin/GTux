import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from gtux import geproton


def make_archive(path: Path, top: str, extra: str | None = None) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in ((f"{top}/proton", b"#!/bin/sh\n"), (f"{top}/version", b"1\n")):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if extra:
            info = tarfile.TarInfo(extra)
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))


class GEProtonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def release(self, extra=None, damage=False):
        tag = "GE-Proton11-11"
        name = f"{tag}-x86_64.tar.gz"
        archive = self.dir / name
        make_archive(archive, f"{tag}-x86_64", extra)  # как в настоящем релизе: папка с суффиксом
        digest = hashlib.sha512(archive.read_bytes()).hexdigest()
        if damage:
            digest = "0" * 128
        (self.dir / "sum").write_text(f"{digest}  {name}\n")
        return {"tag": tag, "name": name, "archive": archive.as_uri(), "sha512": (self.dir / "sum").as_uri()}

    def test_install_checks_sum_and_extracts(self):
        target = self.dir / "compatibilitytools.d"
        path = geproton.install(target, release=self.release())
        self.assertEqual(path, target / "GE-Proton11-11-x86_64")
        self.assertTrue((path / "proton").is_file())
        self.assertEqual([p.name for p in target.iterdir()], ["GE-Proton11-11-x86_64"])  # без временных папок
        self.assertEqual(geproton.install(target, release=self.release()), path)  # повторно — ничего не делает

    def test_bad_checksum_installs_nothing(self):
        target = self.dir / "c"
        with self.assertRaises(geproton.GEError):
            geproton.install(target, release=self.release(damage=True))
        self.assertEqual(list(target.iterdir()), [])

    def test_path_escape_rejected(self):
        target = self.dir / "c"
        with self.assertRaises(geproton.GEError):
            geproton.install(target, release=self.release(extra="../evil"))
        self.assertFalse((self.dir / "evil").exists())
        self.assertEqual(list(target.iterdir()), [])

    def test_sha512_line(self):
        h = "a" * 128
        self.assertEqual(geproton.expected_sha512(f"{h}  GE-Proton11-11-x86_64.tar.gz\n",
                                                  "GE-Proton11-11-x86_64.tar.gz"), h)
        with self.assertRaises(geproton.GEError):
            geproton.expected_sha512(f"{h}  other.tar.gz", "GE-Proton11-11-x86_64.tar.gz")
