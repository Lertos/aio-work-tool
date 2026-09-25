import tempfile
import unittest

from src.model.items import SurroundItem
from src.model.storage import MemorySecrets, Storage
from src.services.surround import surround


class SurroundTests(unittest.TestCase):
    def test_trims_and_wraps_each_line(self):
        item = SurroundItem("'", "',")
        self.assertEqual(surround("  a \nb\t\n c", item), "'a',\n'b',\n'c',")

    def test_remove_final_suffix(self):
        item = SurroundItem("", ",", remove_final_suffix=True)
        self.assertEqual(surround("a\nb\nc", item), "a,\nb,\nc")

    def test_remove_final_keeps_closing_quote(self):
        item = SurroundItem("'", "',", remove_final_suffix=True)
        self.assertEqual(surround("a\nb\nc", item), "'a',\n'b',\n'c'")

    def test_remove_final_drops_trailing_space_and_semicolon(self):
        self.assertEqual(surround("a\nb", SurroundItem('"', '", ', True)), '"a", \n"b"')
        self.assertEqual(surround("a\nb", SurroundItem("", ");", True)), "a);\nb)")

    def test_remove_final_without_separator_keeps_suffix(self):
        self.assertEqual(surround("a\nb", SurroundItem("[", "]", True)), "[a]\n[b]")

    def test_blank_lines_and_windows_newlines_are_ignored(self):
        item = SurroundItem("[", "],", remove_final_suffix=True)
        self.assertEqual(surround("a\r\n\r\n   \r\nb\r\n", item), "[a],\n[b]")

    def test_single_line_with_remove_final_suffix(self):
        self.assertEqual(surround("x", SurroundItem("'", "',", True)), "'x'")

    def test_empty_clipboard(self):
        self.assertEqual(surround("", SurroundItem("'", "'")), "")
        self.assertEqual(surround(" \n\n", SurroundItem("'", "'")), "")

    def test_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(tmp, MemorySecrets())
            store = storage.load("surround")
            store.add(SurroundItem(" '", "', ", True))
            self.assertEqual(storage.load("surround").active, [SurroundItem(" '", "', ", True)])


if __name__ == "__main__":
    unittest.main()
