import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.model.items import SavedQuery
from src.model.storage import MemorySecrets, Storage
from src.services.saved_query import (QueryResult, ResultSet, remember_database, run_query,
                                      split_batches)

try:
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def query(**kw):
    base = dict(description="Stuck orders", server="SQL01",
                query="SELECT * FROM Orders WHERE Status = 'Stuck'",
                recent_databases=["Sales", "SalesArchive"], connection_string="UID=me;PWD=pw")
    base.update(kw)
    return SavedQuery(**base)


class ServiceTests(unittest.TestCase):
    def test_split_batches_on_go_lines_only(self):
        sql = "SELECT 1\nGO\n  go ;\nSELECT 'GO' AS going\r\nGO\r\n\nUPDATE t SET category = 'go'"
        self.assertEqual(split_batches(sql),
                         ["SELECT 1", "SELECT 'GO' AS going", "UPDATE t SET category = 'go'"])

    def test_remember_database_moves_to_front_without_duplicates(self):
        item = query(recent_databases=["A", "B", "C"])
        self.assertEqual(remember_database(item, "c"), ["c", "A", "B"])
        self.assertEqual(remember_database(item, "New", keep=3), ["New", "A", "B"])

    def test_run_query_builds_connection_for_the_chosen_database(self):
        seen = {}

        def execute(cs, batches):
            seen["cs"], seen["batches"] = cs, batches
            return QueryResult([ResultSet(["n"], [(1,)])])

        result = run_query(query(query="SELECT 1\nGO\nSELECT 2"), "HR", execute)
        self.assertIn("SERVER=SQL01;", seen["cs"])
        self.assertIn("DATABASE={HR}", seen["cs"])
        self.assertIn("UID=me;PWD=pw", seen["cs"])
        self.assertEqual(seen["batches"], ["SELECT 1", "SELECT 2"])
        self.assertEqual(result.result_sets[0].rows, [(1,)])

    def test_connection_string_in_keyring_recent_databases_in_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            secrets = MemorySecrets()
            store = Storage(tmp, secrets).load("queries")
            store.add(query())
            raw = Path(tmp, "queries.json").read_text(encoding="utf-8")
            self.assertNotIn("PWD=pw", raw)
            self.assertIn("SalesArchive", raw)
            self.assertEqual(Storage(tmp, secrets).load("queries").active, [query(id=store[0].id)])


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_run_dialog_prefills_last_database_and_returns_edits(self):
        from src.ui.dialogs.saved_query_dialog import SavedQueryDialog
        item = query()
        dialog = SavedQueryDialog(None, item, run=True)
        self.assertEqual(dialog.database.currentText(), "Sales")
        dialog.database.setEditText("HR")
        dialog.query.setPlainText("SELECT TOP 5 * FROM Orders")
        dialog.validate()
        updated, database = dialog.build_result()
        self.assertEqual(database, "HR")
        self.assertEqual(updated.recent_databases, ["HR", "Sales", "SalesArchive"])
        self.assertEqual(updated.query, "SELECT TOP 5 * FROM Orders")
        self.assertEqual(updated.id, item.id)  # same record, so the keyring entry stays linked
        dialog.deleteLater()

    def test_add_dialog_defaults_display_text_to_first_query_line(self):
        from src.ui.dialogs.saved_query_dialog import SavedQueryDialog
        dialog = SavedQueryDialog(None)
        dialog.server.setText("SQL01")
        dialog.query.setPlainText("\n  -- Find stuck orders\nSELECT 1")
        self.assertEqual(dialog.build_result().description, "-- Find stuck orders")
        dialog.deleteLater()

    def test_cells_format_and_copy_as_tsv(self):
        from src.ui.dialogs.query_results_dialog import ResultTableModel, format_cell, to_tsv
        self.assertEqual(format_cell(None), "NULL")
        self.assertEqual(format_cell(b"\x01\xab"), "0x01AB")
        self.assertEqual(format_cell(datetime(2026, 9, 25, 8, 5, 0)), "2026-09-25 08:05:00")
        self.assertEqual(format_cell(Decimal("1E+2")), "100")
        model = ResultTableModel(ResultSet(["id", "note"], [(1, "a\tb"), (2, None), (3, "x\ny")]))
        self.assertEqual(to_tsv(model.as_rows(headers=True)), "id\tnote\n1\ta b\n2\tNULL\n3\tx y")
        cells = [model.index(0, 1), model.index(2, 0)]  # non-adjacent: blanks fill the gaps
        self.assertEqual(model.as_rows(cells), [["", "a\tb"], ["3", ""]])


if __name__ == "__main__":
    unittest.main()
