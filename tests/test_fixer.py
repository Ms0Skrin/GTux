import unittest

from gtux import fixer, packages
from gtux.models import Action, CheckResult, Context, Status


def r(status, pkgs):
    return CheckResult("x", "g", "t", status, packages=pkgs)


class PlanTest(unittest.TestCase):
    def test_only_problems_and_dedup(self):
        ctx = Context(package_manager=packages.Pacman(), multilib_enabled=True)
        plan = fixer.build_plan([r(Status.FAIL, ["a", "lib32-a"]), r(Status.WARN, ["a", "b"]),
                                 r(Status.OK, ["c"])], ctx)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].argv, ["sudo", "pacman", "-S", "--needed", "a", "lib32-a", "b"])

    def test_arch_multilib_off_skips_lib32(self):
        ctx = Context(package_manager=packages.Pacman(), multilib_enabled=False)
        plan = fixer.build_plan([r(Status.FAIL, ["a", "lib32-a"])], ctx)
        self.assertEqual(plan.skipped, ["lib32-a"])
        self.assertEqual(plan.steps[0].packages, ["a"])

    def test_debian_enables_i386_first(self):
        ctx = Context(package_manager=packages.Apt(), multilib_enabled=False)
        plan = fixer.build_plan([r(Status.FAIL, ["libvulkan1:i386"])], ctx)
        self.assertEqual([s.command for s in plan.steps], [
            "sudo dpkg --add-architecture i386", "sudo apt update", "sudo apt install libvulkan1:i386"])

    def test_no_package_manager(self):
        self.assertEqual(fixer.build_plan([r(Status.FAIL, ["a"])], Context()).steps, [])

    def test_actions_from_problems_only(self):
        sysctl = Action("sysctl", "/etc/sysctl.d/80-x.conf", "vm.max_map_count = 1048576")
        flat = Action("flatpak_filesystem", "/mnt/games", "com.valvesoftware.Steam")
        results = [CheckResult("a", "g", "A", Status.WARN, actions=[sysctl]),
                   CheckResult("b", "g", "B", Status.FAIL, actions=[flat, flat]),
                   CheckResult("c", "g", "C", Status.OK, actions=[Action("sysctl", "/etc/sysctl.d/y.conf", "k = 1")])]
        plan = fixer.build_plan(results, Context())
        self.assertEqual([s.kind for s in plan.steps], ["sysctl", "flatpak_filesystem"])
        self.assertEqual(plan.steps[0].command, "echo 'vm.max_map_count = 1048576' | sudo tee "
                         "/etc/sysctl.d/80-x.conf && sudo sysctl --load=/etc/sysctl.d/80-x.conf")
        self.assertFalse(plan.steps[1].root)
        self.assertEqual(plan.steps[1].argv,
                         ["flatpak", "override", "--user", "--filesystem=/mnt/games", "com.valvesoftware.Steam"])

    def test_root_script_one_password(self):
        ctx = Context(package_manager=packages.Pacman(), multilib_enabled=True)
        results = [r(Status.FAIL, ["a"]),
                   CheckResult("s", "g", "S", Status.WARN, actions=[Action("sysctl", "/etc/sysctl.d/x.conf", "k = 1")]),
                   CheckResult("f", "g", "F", Status.FAIL, actions=[Action("flatpak_filesystem", "/m", "app")])]
        plan = fixer.build_plan(results, ctx)
        self.assertEqual(fixer.root_script(plan.steps, ctx.package_manager).splitlines(), [
            "set -ex", "pacman -S --needed --noconfirm a",
            "printf '%s\\n' 'k = 1' > /etc/sysctl.d/x.conf", "sysctl --load=/etc/sysctl.d/x.conf"])

    def test_execute_stops_on_error(self):
        plan = fixer.Plan([fixer.Step("install", ["true"]), fixer.Step("install", ["false"]),
                           fixer.Step("install", ["true"])])
        seen = []
        ok, failed, code = fixer.execute(plan, lambda step, error=None: seen.append(step))
        self.assertFalse(ok)
        self.assertEqual((failed.argv, code, len(seen)), (["false"], 1, 2))


if __name__ == "__main__":
    unittest.main()


class OffersTest(unittest.TestCase):
    def test_multilib_only_packages_on_arch(self):
        # steam и steam-devices лежат в multilib: без него их ставить нельзя
        ctx = Context(package_manager=packages.Pacman(), multilib_enabled=False)
        plan = fixer.build_plan([r(Status.FAIL, ["steam", "steam-devices", "gamemode"])], ctx)
        self.assertEqual(plan.skipped, ["steam", "steam-devices"])
        self.assertEqual(plan.steps[0].packages, ["gamemode"])
        self.assertTrue(packages.Apt().is_32bit("steam-installer"))

    def test_optional_offered_even_when_ok_and_not_in_steps(self):
        res = CheckResult("apps.lutris", "apps", "Lutris", Status.OK,
                          actions=[Action("package", "lutris", optional=True)])
        heroic = CheckResult("apps.heroic", "apps", "Heroic", Status.OK,
                             actions=[Action("flatpak_app", "com.heroicgameslauncher.hgl", optional=True)])
        ctx = Context(package_manager=packages.Pacman(), multilib_enabled=True, flatpak_apps=set())
        plan = fixer.build_plan([res, heroic], ctx)
        self.assertEqual(plan.steps, [])
        self.assertEqual([s.kind for s in plan.offers], ["install", "flatpak_app"])
        self.assertTrue(all(s.optional for s in plan.offers))
        fp = plan.offers[1]
        self.assertEqual(fp.prereq, [])  # flatpak уже есть
        self.assertFalse(fp.root)
        self.assertEqual(fixer.user_commands(fp)[0][:3], ["flatpak", "remote-add", "--user"])
        self.assertIn("flatpak install --user --noninteractive flathub com.heroicgameslauncher.hgl", fp.command)

    def test_flatpak_missing_adds_package_prereq(self):
        heroic = CheckResult("apps.heroic", "apps", "Heroic", Status.OK,
                             actions=[Action("flatpak_app", "com.heroicgameslauncher.hgl", optional=True)])
        ctx = Context(package_manager=packages.Apt(), flatpak_apps=None)
        step = fixer.build_plan([heroic], ctx).offers[0]
        self.assertEqual([s.command for s in step.chain()][0], "sudo apt install flatpak")
        # в окне: сначала root (flatpak), потом приложение без пароля
        self.assertIn("apt install -y flatpak", fixer.root_script(step.chain(), ctx.package_manager))

    def test_ge_proton_runs_gtux_itself(self):
        res = CheckResult("proton.custom", "proton", "GE", Status.WARN,
                          actions=[Action("ge_proton", "/home/u/.local/share/Steam/compatibilitytools.d",
                                          optional=True)])
        step = fixer.build_plan([res], Context()).offers[0]
        self.assertEqual(step.argv[1:], ["-m", "gtux", "--install-ge",
                                         "/home/u/.local/share/Steam/compatibilitytools.d"])
        self.assertIn("PYTHONPATH", fixer.step_env(step))


class RiskyTest(unittest.TestCase):
    STD = "[core]\nInclude = /etc/pacman.d/mirrorlist\n\n#[multilib-testing]\n#Include = /etc/pacman.d/mirrorlist\n\n" \
          "#[multilib]\n#Include = /etc/pacman.d/mirrorlist\n\n[custom]\nServer = file:///x\n"

    def test_multilib_lines(self):
        from gtux.checks.multilib import multilib_lines
        self.assertEqual(multilib_lines(self.STD), [7, 8])
        self.assertIsNone(multilib_lines("[core]\nInclude = x\n"))          # раздела нет
        self.assertIsNone(multilib_lines("#[multilib]\n\n#Include = x\n"))  # Include оторван — руками

    def test_multilib_step_edits_only_its_lines_with_guard_and_backup(self):
        import subprocess
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "pacman.conf"
            conf.write_text(self.STD)
            step = fixer.multilib_step(str(conf), [7, 8], "multilib")
            self.assertTrue(step.optional and step.warning)
            self.assertIn("sha256sum -c", step.command)
            self.assertEqual([s.kind for s in step.chain()], ["enable_multilib", "system_upgrade"])
            # выполняем то же, что root-сценарий, но без sudo и без pacman
            script = fixer.root_script([step], packages.Pacman()).replace("pacman -Syu --noconfirm", "true")
            subprocess.run(["sh", "-c", script], check=True, capture_output=True)
            text = conf.read_text()
            self.assertIn("\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n", text)
            self.assertIn("#[multilib-testing]", text)  # соседний раздел не тронут
            self.assertEqual(Path(step.backup).read_text(), self.STD)
            # файл изменился после проверки — сценарий останавливается и ничего не меняет
            conf.write_text(self.STD + "# changed\n")
            step2 = fixer.multilib_step(str(conf), [7, 8])
            conf.write_text(self.STD + "# changed again\n")
            script2 = fixer.root_script([step2], packages.Pacman()).replace("pacman -Syu --noconfirm", "true")
            self.assertNotEqual(subprocess.run(["sh", "-c", script2], capture_output=True).returncode, 0)
            self.assertEqual(conf.read_text(), self.STD + "# changed again\n")

    def test_multilib_offer_installs_skipped_packages_after(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "pacman.conf"
            conf.write_text(self.STD)
            res = [CheckResult("multilib.repo", "multilib", "multilib", Status.FAIL,
                               actions=[Action("pacman_multilib", str(conf), "7,8", optional=True)]),
                   r(Status.FAIL, ["lib32-vulkan-icd-loader", "steam"])]
            plan = fixer.build_plan(res, Context(package_manager=packages.Pacman(), multilib_enabled=False))
            chain = plan.offers[0].chain()
            self.assertEqual([s.kind for s in chain], ["enable_multilib", "system_upgrade", "install"])
            self.assertEqual(chain[-1].packages, ["lib32-vulkan-icd-loader", "steam"])
            self.assertIn("pacman -Syu --noconfirm", fixer.root_script(chain, packages.Pacman()))

    def test_protontricks_and_upgrade_are_optional(self):
        res = [CheckResult("logs.proton.1", "logs", "log", Status.FAIL,
                           actions=[Action("protontricks", "1091500", "vcrun2022 d3dcompiler_47", optional=True)]),
               CheckResult("multilib.nvidia_match", "multilib", "nv", Status.FAIL,
                           actions=[Action("system_upgrade", "pacman", optional=True)])]
        plan = fixer.build_plan(res, Context(package_manager=packages.Pacman()))
        self.assertEqual(plan.steps, [])
        self.assertEqual(plan.offers[0].argv, ["protontricks", "1091500", "-q", "vcrun2022", "d3dcompiler_47"])
        self.assertFalse(plan.offers[0].root)
        self.assertEqual(plan.offers[1].command, "sudo pacman -Syu")
