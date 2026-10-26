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
