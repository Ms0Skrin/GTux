import struct
import unittest

from gtux import i18n, knowledge, library
from gtux.models import Status


def appinfo_v29(apps: dict[int, dict]) -> bytes:
    """Маленький appinfo.vdf версии 29: записи с двоичным KeyValues и таблица строк в конце."""
    strings: list[str] = []

    def key(k):
        if k not in strings:
            strings.append(k)
        return struct.pack("<i", strings.index(k))

    def kv(node):
        out = b""
        for k, v in node.items():
            if isinstance(v, dict):
                out += b"\x00" + key(k) + kv(v)
            elif isinstance(v, int):
                out += b"\x02" + key(k) + struct.pack("<i", v)
            else:
                out += b"\x01" + key(k) + v.encode() + b"\0"
        return out + b"\x08"

    body = b""
    for appid, common in apps.items():
        data = b"\0" * library.ENTRY_HEADER + kv({"appinfo": {"appid": appid, "common": common}})
        body += struct.pack("<II", appid, len(data)) + data
    body += struct.pack("<I", 0)
    table_off = 16 + len(body)
    table = struct.pack("<I", len(strings)) + b"".join(s.encode() + b"\0" for s in strings)
    return struct.pack("<IIq", library.MAGIC_V29, 1, table_off) + body + table


class AppInfoTest(unittest.TestCase):
    def test_parse_v29(self):
        data = appinfo_v29({
            1771300: {"name": "Kingdom Come: Deliverance II", "type": "Game", "oslist": "windows"},
            227300: {"name": "Euro Truck Simulator 2", "type": "game", "oslist": "windows,macos,linux"},
            1493710: {"name": "Proton Experimental", "type": "Tool"},
        })
        info = library.parse_appinfo(data)
        self.assertEqual(set(info), {"1771300", "227300", "1493710"})
        self.assertEqual(info["227300"]["oslist"], "windows,macos,linux")
        self.assertEqual(set(library.parse_appinfo(data, {"227300"})), {"227300"})  # только нужные

    def test_bad_version(self):
        with self.assertRaises(library.AppInfoError):
            library.parse_appinfo(struct.pack("<IIq", 0x12345678, 1, 0))


class SummaryTest(unittest.TestCase):
    def setUp(self):
        i18n.set_language("ru")

    def test_broken_and_anticheat(self):
        stat = knowledge.ProtonStat("official", 12, 0)
        broken = knowledge.ProtonPick(None, [stat], True, [], broken=True)
        g = library.LibraryGame("1", "X", True, False, broken, {"status": "Denied"})
        status, parts = library.summary(g)
        self.assertEqual(status, Status.FAIL)
        self.assertIn("античит не пускает Linux", parts)
        ok = knowledge.ProtonStat("native", 16, 16)
        g2 = library.LibraryGame("2", "Y", False, True, knowledge.ProtonPick(ok, [ok], True, []), None)
        status2, parts2 = library.summary(g2)
        self.assertEqual(status2, Status.OK)
        self.assertEqual(parts2[:2], ["не установлена", "есть Linux-версия"])
        self.assertEqual(library.summary(library.LibraryGame("3", "Z", False, False, None, None))[0], Status.UNKNOWN)
