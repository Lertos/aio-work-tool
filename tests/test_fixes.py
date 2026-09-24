"""Regression tests for the three Java bugs fixed in the port, plus JSON storage.

Run from the project folder:  python -m unittest -v
The Qt tests are skipped automatically if PySide6 isn't installed.
"""
import json
import tempfile
import unittest
from pathlib import Path

from src.model.item_store import ItemStore
from src.model.items import (PromoteItem, PromoteType, ServerConfig, SQLCompareItem,
                                       SQLType, TodoItem)
from src.model.storage import MemorySecrets, Storage
from src.services.sql_compare import compare

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialogButtonBox
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


# ----------------------------------------------------------------- bug #3
class UndoVisibilityTests(unittest.TestCase):
    def test_undo_visible_until_history_is_empty(self):
        store = ItemStore([TodoItem("a"), TodoItem("b"), TodoItem("c")])
        seen = []
        store.subscribe(lambda: seen.append(store.has_history))

        store.move_to_history(0)
        store.move_to_history(0)
        self.assertEqual(seen, [True, True])

        store.restore_last()          # one item still in history -> must stay visible
        self.assertTrue(seen[-1])     # the Java To-Do tab hid the button here
        store.restore_last()
        self.assertFalse(seen[-1])

    def test_delete_checked_moves_only_done_items(self):
        store = ItemStore([TodoItem("a", done=True), TodoItem("b"), TodoItem("c", done=True)])
        self.assertEqual(store.remove_where(lambda i: i.done), 2)
        self.assertEqual([i.description for i in store.active], ["b"])
        self.assertTrue(store.has_history)

    def test_move_inserts_rather_than_swaps(self):
        store = ItemStore([TodoItem(x) for x in "abcd"])
        store.move(0, 2)
        self.assertEqual([i.description for i in store.active], list("bcad"))


# ----------------------------------------------------------------- bug #2
def _item(servers):
    return SQLCompareItem("test", "usp_x", SQLType.MYSQL,
                          [ServerConfig(name, "h", databases=dbs) for name, dbs in servers])


class SqlCompareTests(unittest.TestCase):
    def test_detects_difference_between_servers(self):
        defs = {("prod", "db1"): "SELECT 1", ("prod", "db2"): "SELECT 1",
                ("test", "db1"): "SELECT 2"}
        report = compare(_item([("prod", ["db1", "db2"]), ("test", ["db1"])]),
                         fetch=lambda t, s, d, p: defs[(s.tab_name, d)])
        self.assertFalse(report.all_match)   # the Java version reported "All definitions match"
        self.assertEqual(len(report.groups), 2)
        self.assertEqual([str(l) for l in report.groups[1]], ["test / db1"])

    def test_ignores_whitespace_and_case(self):
        defs = {"a": "SELECT  1\n FROM t", "b": "select 1 from\tT"}
        report = compare(_item([("s1", ["a"]), ("s2", ["b"])]),
                         fetch=lambda t, s, d, p: defs[d])
        self.assertTrue(report.all_match)

    def test_missing_and_errors_are_reported_not_fatal(self):
        def fetch(t, s, d, p):
            if d == "gone":
                return None
            if d == "down":
                raise ConnectionError("timed out")
            return "SELECT 1"
        report = compare(_item([("s", ["ok", "gone", "down"])]), fetch=fetch)
        self.assertFalse(report.all_match)
        self.assertEqual([str(l) for l in report.missing], ["s / gone"])
        self.assertIn("timed out", report.summary())


# ----------------------------------------------------------------- storage
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.secrets = MemorySecrets()
        self.storage = Storage(self.tmp.name, self.secrets)

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_with_enums_and_history(self):
        store = self.storage.load("promote")
        store.add(PromoteItem("p", promote_type=PromoteType.MOVE, origin_paths=["C:/a"]))
        store.add(PromoteItem("q"))
        store.move_to_history(1)
        again = self.storage.load("promote")
        self.assertEqual(again.active[0].promote_type, PromoteType.MOVE)
        self.assertEqual(again.history[0].description, "q")

    def test_passwords_go_to_secret_store_not_json(self):
        store = self.storage.load("sql_compare")
        store.add(SQLCompareItem("x", "usp", SQLType.TRANSACT_SQL,
                                 [ServerConfig("prod", "h", username="u", password="hunter2")]))
        raw = Path(self.tmp.name, "sql_compare.json").read_text()
        self.assertNotIn("hunter2", raw)
        self.assertIn("hunter2", self.secrets.data.values())
        again = self.storage.load("sql_compare")
        self.assertEqual(again.active[0].servers[0].password, "hunter2")

    def test_corrupt_file_is_set_aside(self):
        Path(self.tmp.name, "todo.json").write_text("{not json")
        store = self.storage.load("todo")
        self.assertEqual(len(store), 0)
        self.assertTrue(Path(self.tmp.name, "todo.json.bad").exists())

    def test_file_format(self):
        self.storage.load("todo").add(TodoItem("buy milk"))
        raw = json.loads(Path(self.tmp.name, "todo.json").read_text())
        self.assertEqual(raw["version"], 1)
        self.assertEqual(raw["active"][0]["description"], "buy milk")


# ----------------------------------------------------------------- bug #1 (needs Qt)
@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class DialogCancelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _run(self, press_accept: bool):
        from PySide6.QtWidgets import QApplication as App
        from src.ui.dialogs.promote_dialog import Mode, PromoteDialog

        def click():
            dlg = App.activeModalWidget()
            if press_accept:
                dlg.accept_button.click()
            else:
                dlg.buttons.button(QDialogButtonBox.StandardButton.Cancel).click()

        QTimer.singleShot(50, click)
        item = PromoteItem("p", file_names=["f.txt"], origin_paths=["C:/a"],
                           destination_paths=["C:/b"])
        return PromoteDialog.ask(None, item, mode=Mode.RUN)

    def test_cancel_after_a_successful_run_returns_none(self):
        self.assertIsNotNone(self._run(press_accept=True))
        self.assertIsNone(self._run(press_accept=False))  # Java returned the previous item here


if __name__ == "__main__":
    unittest.main()
