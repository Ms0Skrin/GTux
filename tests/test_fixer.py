import unittest

from doctor import fixer, packages
from doctor.models import CheckResult, Context, Status


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

    def test_execute_stops_on_error(self):
        plan = fixer.Plan([fixer.Step("install", ["true"]), fixer.Step("install", ["false"]),
                           fixer.Step("install", ["true"])])
        seen = []
        ok, failed, code = fixer.execute(plan, lambda step, error=None: seen.append(step))
        self.assertFalse(ok)
        self.assertEqual((failed.argv, code, len(seen)), (["false"], 1, 2))


if __name__ == "__main__":
    unittest.main()
