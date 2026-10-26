import io
import json
import unittest

from doctor import knowledge
from doctor.knowledge import Profile


def report(appid, opts, gpu="NVIDIA GeForce RTX 3060 Ti", ts=10**10):
    return {"app": {"steam": {"appId": appid}}, "responses": {"launchOptions": opts},
            "systemInfo": {"gpu": gpu}, "timestamp": ts}


class SafeTokensTest(unittest.TestCase):
    def test_whitelist_only(self):
        self.assertEqual(knowledge.safe_tokens(
            'PROTON_NO_ESYNC=1 LD_PRELOAD="" FOO=1 gamemoderun prime-run %command% -novid +x 1 ; rm'),
            {"PROTON_NO_ESYNC=1", "gamemoderun", "arg:-novid", "arg:+x"})
        self.assertEqual(knowledge.safe_tokens("mangohud %command%"), set())

    def test_bad_values_and_shell(self):
        self.assertEqual(knowledge.safe_tokens("PROTON_NO_ESYNC=$(rm) %command%"), set())
        self.assertEqual(knowledge.safe_tokens("bash -c 'x'"), set())
        self.assertEqual(knowledge.safe_tokens('WINEDLLOVERRIDES="winmm=n,b" %command%'),
                         {"WINEDLLOVERRIDES=winmm=n,b"})


class TipsTest(unittest.TestCase):
    def setUp(self):
        reps = ([report("1", "PROTON_ENABLE_NVAPI=1 gamemoderun %command%")] * 4
                + [report("1", "PROTON_FSR4_UPGRADE=1 %command%", gpu="AMD Radeon RX 9070")] * 6
                + [report("1", "game-performance %command%")] * 3
                + [report("1", "%command% -onSteamDeck")] * 3
                + [report("1", "PROTON_NO_ESYNC=1 %command%", ts=1)] * 10)  # старые — не считаем
        stream = io.BytesIO(json.dumps(reps).encode())
        self.data = {"games": knowledge.summarize_reports(knowledge.iter_reports(stream), since=100)}

    def test_personal_nvidia(self):
        prof = Profile("nvidia", False, frozenset({"game-performance"}))
        tips = {t.token: t for t in knowledge.tips_for("1", prof, self.data)}
        self.assertEqual(set(tips), {"PROTON_ENABLE_NVAPI=1", "gamemoderun", "game-performance"})  # без -onSteamDeck
        self.assertEqual(tips["PROTON_ENABLE_NVAPI=1"].builds, ("ge",))
        self.assertFalse(knowledge.works_with(tips["PROTON_ENABLE_NVAPI=1"], "proton-cachyos-11.0-x86_64_v3"))
        self.assertTrue(knowledge.works_with(tips["PROTON_ENABLE_NVAPI=1"], "ge-proton10-25"))
        self.assertTrue(knowledge.works_with(tips["gamemoderun"], "proton_experimental"))
        self.assertTrue(tips["PROTON_ENABLE_NVAPI=1"].same_vendor)
        self.assertEqual((tips["gamemoderun"].count, tips["gamemoderun"].reports), (4, 10))
        self.assertEqual(tips["gamemoderun"].missing_tool, "gamemoderun")
        # game-performance есть только в CachyOS: без него совет не показываем вовсе
        other = knowledge.tips_for("1", Profile("nvidia", False, frozenset()), self.data)
        self.assertNotIn("game-performance", [t.token for t in other])

    def test_personal_amd_gets_no_nvidia_tips(self):
        tips = [t.token for t in knowledge.tips_for("1", Profile("amd", False, frozenset()), self.data)]
        self.assertEqual(tips, ["PROTON_FSR4_UPGRADE=1"])

    def test_latest_dump_and_ge(self):
        self.assertEqual(knowledge.latest_dump_name(
            ["reports_sep2_2022.tar.gz", "reports_sep1_2026.tar.gz", "reports_aug1_2026.tar.gz", "x"]),
            "reports_sep1_2026.tar.gz")
        self.assertEqual(knowledge.build_family("ge-proton10-25"), "ge")
        self.assertEqual(knowledge.build_family("proton-cachyos-11.0-20261005-slr-x86_64_v3"), "cachyos")
        self.assertEqual(knowledge.build_family("proton_experimental"), "valve")
        self.assertEqual(knowledge.build_family(None), "valve")
        self.assertEqual(knowledge.gpu_vendor("AMD Custom GPU 0405"), "amd")


if __name__ == "__main__":
    unittest.main()


class DownloadTest(unittest.TestCase):
    def test_resume_after_drop(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        payload = bytes(range(256)) * 1000
        calls = []

        class Resp:
            def __init__(self, data, status, fail_after=None):
                self.data, self.status, self.fail_after, self.pos = data, status, fail_after, 0
                self.headers = {"Content-Length": str(len(data))}

            def read(self, n):
                if self.fail_after is not None and self.pos >= self.fail_after:
                    raise TimeoutError("timed out")
                chunk = self.data[self.pos:self.pos + min(n, 1000)]
                self.pos += len(chunk)
                return chunk

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout):
            rng = req.get_header("Range")
            calls.append(rng)
            if rng is None:
                return Resp(payload, 200, fail_after=50_000)
            start = int(rng.split("=")[1].rstrip("-"))
            return Resp(payload[start:], 206)

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(knowledge.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(knowledge.time, "sleep", lambda s: None):
            dest = Path(tmp) / "f"
            knowledge.download("https://example.invalid/f", dest, lambda d, t: None)
            self.assertEqual(dest.read_bytes(), payload)
        self.assertEqual(calls, [None, "bytes=50000-"])
