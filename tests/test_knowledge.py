import io
import json
import unittest

from gtux import knowledge
from gtux.knowledge import Profile


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


def proton_report(appid, variant, works=True, gpu="NVIDIA GeForce RTX 3060 Ti", version=None, ts=10**10):
    resp = {"variant": variant, "verdict": "yes" if works else "no"}
    if version:
        resp["customProtonVersion" if variant == "ge" else "protonVersion"] = version
    return {"app": {"steam": {"appId": appid}}, "responses": resp, "systemInfo": {"gpu": gpu}, "timestamp": ts}


class ProtonPickTest(unittest.TestCase):
    NV = Profile("nvidia", False, frozenset())

    def summarize(self, reps, proton_since=100):
        stream = io.BytesIO(json.dumps(reps).encode())
        return {"games": knowledge.summarize_reports(knowledge.iter_reports(stream), since=100,
                                                     proton_since=proton_since)}

    def test_best_for_same_gpu(self):
        reps = ([proton_report("1", "official")] * 9 + [proton_report("1", "official", works=False)] * 3
                + [proton_report("1", "ge", version="GE-Proton10-34")] * 8
                + [proton_report("1", "official", gpu="AMD Radeon RX 9070")] * 20
                + [proton_report("1", "notListed")] * 50                  # неизвестная сборка — не считаем
                + [proton_report("1", "official", works=False, ts=1)] * 50)  # старые — не считаем
        data = self.summarize(reps)
        pick = knowledge.proton_for("1", self.NV, data)
        self.assertTrue(pick.same_vendor)
        self.assertEqual((pick.best.variant, pick.best.works, pick.best.reports), ("ge", 8, 8))
        self.assertEqual(pick.versions, ["GE-Proton10-34"])
        # у AMD только официальный — для AMD он и лучший
        self.assertEqual(knowledge.proton_for("1", Profile("amd", False, frozenset()), data).best.variant, "official")

    def test_close_prefers_simplest(self):
        reps = [proton_report("1", "official")] * 30 + [proton_report("1", "ge")] * 31
        pick = knowledge.proton_for("1", self.NV, self.summarize(reps))
        self.assertEqual(pick.best.variant, "official")  # почти поровну — официальный проще поставить
        self.assertTrue(pick.close)

    def test_broken_and_few(self):
        reps = [proton_report("1", "official", works=False)] * 10 + [proton_report("1", "ge")]
        reps += [proton_report("2", "official")] * 2 + [proton_report("2", "ge")]
        data = self.summarize(reps)
        pick = knowledge.proton_for("1", self.NV, data)
        self.assertTrue(pick.broken)
        self.assertIsNone(pick.best)
        self.assertIsNone(knowledge.proton_for("2", self.NV, data).best)  # 2 отчёта на сборку — мало
        self.assertIsNone(knowledge.proton_for("3", self.NV, data))

    def test_variants_and_advice(self):
        installed = knowledge.installed_variants(
            ["Proton 9.0 (Beta)", "Proton 10.0", "Proton - Experimental"],
            ["GE-Proton10-25", "GE-Proton11-9", "proton-cachyos-slr"])
        self.assertEqual(installed["official"], ["Proton 10.0", "Proton 9.0 (Beta)"])
        self.assertEqual(installed["ge"], ["GE-Proton11-9", "GE-Proton10-25"])
        self.assertEqual(installed["cachyos"], ["proton-cachyos-slr"])
        for tool, var in (("proton_10", "official"), ("proton_experimental", "experimental"),
                          ("ge-proton11-9", "ge"), ("proton-cachyos-slr", "cachyos"), (None, "none")):
            self.assertEqual(knowledge.variant_of(tool), var)
        pick = knowledge.proton_for("1", self.NV, self.summarize([proton_report("1", "ge")] * 5))
        adv = knowledge.advise(pick, "proton-cachyos-slr", installed)
        self.assertEqual((adv.current, adv.use, adv.missing, adv.matches), ("cachyos", "GE-Proton11-9", False, False))
        self.assertTrue(knowledge.advise(pick, "ge-proton10-25", installed).matches)
        self.assertTrue(knowledge.advise(pick, None, {}).missing)
        # Linux-версия без выбранной вручную сборки: текущий вариант — native, сборка по умолчанию не считается
        native = knowledge.proton_for("1", self.NV, self.summarize([proton_report("1", "native")] * 5))
        self.assertTrue(knowledge.advise(native, None, installed, native=True).matches)
        self.assertEqual(knowledge.advise(pick, None, installed, native=True).current, "native")
