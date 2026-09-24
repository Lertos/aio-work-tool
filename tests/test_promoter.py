import tempfile
import unittest
from pathlib import Path

from src.model.items import PathType, PromoteItem, PromoteType
from src.services import promoter


class PromoterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.src, self.dst1, self.dst2 = root / "src", root / "d1", root / "d2"
        for d in (self.src, self.dst1, self.dst2):
            d.mkdir()
        (self.src / "a.txt").write_text("A")
        (self.src / "b.txt").write_text("B")

    def tearDown(self):
        self._tmp.cleanup()

    def item(self, **kw):
        base = dict(description="t", path_type=PathType.FILE_NAMES_SEPARATE,
                    promote_type=PromoteType.COPY, file_names=["a.txt", "b.txt"],
                    origin_paths=[str(self.src)], destination_paths=[str(self.dst1)])
        base.update(kw)
        return PromoteItem(**base)

    def test_copy_separate_file_names(self):
        result = promoter.promote(self.item())
        self.assertEqual(result.errors, [])
        self.assertEqual((self.dst1 / "b.txt").read_text(), "B")
        self.assertTrue((self.src / "a.txt").exists())

    def test_copy_overwrites_existing(self):
        (self.dst1 / "a.txt").write_text("old")
        promoter.promote(self.item())
        self.assertEqual((self.dst1 / "a.txt").read_text(), "A")

    def test_move_to_two_destinations(self):
        item = self.item(promote_type=PromoteType.MOVE,
                         destination_paths=[str(self.dst1), str(self.dst2)])
        result = promoter.promote(item)
        self.assertEqual(result.errors, [])
        for d in (self.dst1, self.dst2):
            self.assertEqual((d / "a.txt").read_text(), "A")
        self.assertFalse((self.src / "a.txt").exists())  # moved away only after the last copy

    def test_paths_include_file_names(self):
        item = self.item(path_type=PathType.FILE_NAMES_IN_PATHS, file_names=[],
                         origin_paths=[str(self.src / "a.txt")],
                         destination_paths=[str(self.dst1), str(self.dst2 / "renamed.txt")])
        self.assertEqual(promoter.validate(item), [])
        result = promoter.promote(item)
        self.assertEqual(result.errors, [])
        self.assertTrue((self.dst1 / "a.txt").exists())
        self.assertEqual((self.dst2 / "renamed.txt").read_text(), "A")

    def test_validate_reports_every_problem(self):
        item = self.item(file_names=["a.txt", "missing.txt"],
                         destination_paths=[str(self.dst1 / "nope")])
        problems = promoter.validate(item)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("missing.txt" in p for p in problems))

    def test_errors_are_collected(self):
        item = self.item(file_names=["a.txt", "missing.txt"])
        result = promoter.promote(item)
        self.assertEqual(len(result.promoted), 1)
        self.assertEqual(len(result.errors), 1)


if __name__ == "__main__":
    unittest.main()
