"""Части окна, которые можно проверить без дисплея. Пропускается, если нет PyGObject/GTK4."""

import unittest

try:
    from gtux.gui import app, style
except (ImportError, ValueError):
    app = None


@unittest.skipIf(app is None, "нет GTK4/libadwaita/PyGObject")
class GuiHelpersTest(unittest.TestCase):
    def test_linkify_escapes_and_links(self):
        out = app.linkify("a < b, см. https://www.protondb.com/app/1 и всё")
        self.assertIn("a &lt; b", out)
        self.assertIn('<a href="https://www.protondb.com/app/1">', out)

    def test_worst(self):
        from gtux.models import CheckResult, Status
        rs = [CheckResult("a", "g", "t", Status.OK), CheckResult("b", "g", "t", Status.WARN)]
        self.assertEqual(app.worst(rs), Status.WARN)

    def test_css_has_all_statuses(self):
        for palette in (style.LIGHT, style.DARK):
            css = style.css(palette)
            for s in ("ok", "warn", "fail", "unknown"):
                self.assertIn(f".chip.{s}", css)


if __name__ == "__main__":
    unittest.main()
