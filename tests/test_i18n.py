import re
import unittest

from gtux import gamedb
from gtux.i18n import en, ru

PLACEHOLDER = re.compile(r"\{(\w+)\}")


class I18nTest(unittest.TestCase):
    def test_same_keys(self):
        self.assertEqual(set(ru.TEXTS) - set(en.TEXTS), set(), "нет в en.py")
        self.assertEqual(set(en.TEXTS) - set(ru.TEXTS), set(), "нет в ru.py")

    def test_same_placeholders(self):
        for key, text in ru.TEXTS.items():
            self.assertEqual(set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(en.TEXTS[key])), key)

    def test_no_cyrillic_in_english(self):
        for key, text in en.TEXTS.items():
            self.assertIsNone(re.search(r"[а-яА-ЯёЁ]", text), key)

    def test_game_notes_have_both_languages(self):
        for appid, entry in gamedb.notes_db().items():
            if "notes" in entry:
                self.assertEqual(set(entry["notes"]), {"ru", "en"}, appid)


if __name__ == "__main__":
    unittest.main()
