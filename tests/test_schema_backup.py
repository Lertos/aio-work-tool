import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.model.items import SchemaEnvironment
from src.model.storage import MemorySecrets, Storage
from src.services.odbc import _parse
from src.services.schema_backup import (backup, connection_string, safe_filename,
                                        split_names)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

NOW = datetime(2026, 9, 25, 14, 30, 12)
D18 = "{ODBC Driver 18 for SQL Server}"


def env(conn="", **kw):
    return SchemaEnvironment(kw.pop("description", "Prod"), kw.pop("server", "SQL01"),
                             ["Sales", "HR"], connection_string=conn, **kw)


class ConnectionStringTests(unittest.TestCase):
    def test_blank_uses_windows_login(self):
        self.assertEqual(connection_string(env(), "Sales", D18),
                         "DRIVER={ODBC Driver 18 for SQL Server};SERVER=SQL01;"
                         "DATABASE={Sales};Trusted_Connection=yes")

    def test_user_settings_kept_and_no_trusted_when_login_given(self):
        cs = connection_string(env("UID=me;PWD={a;b}};c};TrustServerCertificate=yes"), "HR", D18)
        self.assertIn("UID=me;PWD={a;b}};c};TrustServerCertificate=yes", cs)
        self.assertNotIn("Trusted_Connection", cs)
        self.assertTrue(cs.startswith("DRIVER={ODBC Driver 18 for SQL Server};SERVER=SQL01;"))

    def test_full_string_keeps_its_server_and_driver_but_database_is_replaced(self):
        cs = connection_string(
            env("Driver={ODBC Driver 17 for SQL Server};Data Source=OTHER;Initial Catalog=master;"
                "Trusted_Connection=yes"), "Sales", D18)
        pairs = dict((k.lower(), v) for k, v in _parse(cs))
        self.assertEqual(pairs["driver"], "{ODBC Driver 17 for SQL Server}")
        self.assertEqual(pairs["data source"], "OTHER")
        self.assertNotIn("server", pairs)
        self.assertNotIn("initial catalog", pairs)
        self.assertEqual(pairs["database"], "{Sales}")


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_one_file_per_entity_per_database(self):
        calls = []

        def fetch(cs, entities):
            calls.append(cs)
            return {e: f"CREATE PROCEDURE {e}\r\nAS SELECT 1" for e in entities}

        result = backup(env(), ["Sales", "HR"], ["dbo.usp_A", "usp_B"], self.root, fetch, NOW)
        folder = self.root / "Prod 2026-09-25 143012"
        self.assertEqual(result.folder, folder)
        self.assertEqual(len(calls), 2)  # one connection per database, not per entity
        self.assertEqual(sorted(p.relative_to(folder).as_posix() for p in result.saved),
                         ["HR/dbo.usp_A.sql", "HR/usp_B.sql", "Sales/dbo.usp_A.sql", "Sales/usp_B.sql"])
        # Line endings are written exactly as the server returned them.
        self.assertEqual((folder / "Sales" / "usp_B.sql").read_bytes(),
                         b"CREATE PROCEDURE usp_B\r\nAS SELECT 1")

    def test_missing_entities_and_connection_errors_are_reported_per_database(self):
        def fetch(cs, entities):
            if "{HR}" in cs:
                raise RuntimeError("Login failed")
            return {"usp_A": "CREATE PROCEDURE usp_A AS SELECT 1", "usp_Gone": None}

        result = backup(env(), ["Sales", "HR"], ["usp_A", "usp_Gone"], self.root, fetch, NOW)
        self.assertEqual(len(result.saved), 1)
        self.assertEqual(result.missing, {"Sales": ["usp_Gone"]})
        self.assertEqual(result.errors, {"HR": "Login failed"})
        summary = result.summary()
        self.assertIn("Sales: usp_Gone", summary)
        self.assertIn("HR: Login failed", summary)

    def test_nothing_found_creates_no_folder(self):
        result = backup(env(), ["Sales"], ["x"], self.root, lambda cs, e: {"x": None}, NOW)
        self.assertEqual(result.saved, [])
        self.assertFalse(result.folder.exists())

    def test_names_and_filenames(self):
        self.assertEqual(split_names("a, b\n\n  A \nc"), ["a", "b", "c"])
        self.assertEqual(safe_filename("[dbo].[usp:x/y]"), "[dbo].[usp_x_y]")
        self.assertEqual(safe_filename(r"SQL01\INST 2026"), "SQL01_INST 2026")


class StorageTests(unittest.TestCase):
    def test_connection_string_goes_to_keyring_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            secrets = MemorySecrets()
            storage = Storage(tmp, secrets)
            store = storage.load("schema_backup")
            item = env("UID=me;PWD=hunter2")
            store.add(item)
            raw = Path(tmp, "schema_backup.json").read_text(encoding="utf-8")
            self.assertNotIn("hunter2", raw)
            self.assertEqual(json.loads(raw)["active"][0]["databases"], ["Sales", "HR"])
            self.assertEqual(Storage(tmp, secrets).load("schema_backup").active, [item])
            self.assertEqual(Storage(tmp, secrets).load("schema_backup")[0].connection_string,
                             "UID=me;PWD=hunter2")


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class CheckComboBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_toggling_updates_checked_items_and_text(self):
        from src.ui.widgets import CheckComboBox
        box = CheckComboBox(["Sales", "HR", "Ops"])
        self.assertEqual(box.checked_items(), [])
        box._toggle(box.model().index(0, 0))
        box._toggle(box.model().index(2, 0))
        self.assertEqual(box.checked_items(), ["Sales", "Ops"])
        self.assertEqual(box.lineEdit().text(), "Sales, Ops")
        box._toggle(box.model().index(0, 0))
        self.assertEqual(box.checked_items(), ["Ops"])

    def test_run_dialog_prefers_typed_databases(self):
        from src.ui.dialogs.schema_backup_run_dialog import SchemaBackupRunDialog
        dialog = SchemaBackupRunDialog(None, env())
        dialog.entities.setPlainText("usp_A\nusp_B")
        dialog.databases._toggle(dialog.databases.model().index(0, 0))
        self.assertEqual(dialog._chosen_databases(), ["Sales"])
        dialog.manual.setPlainText("Temp1\nTemp2")
        self.assertFalse(dialog.databases.isEnabled())
        self.assertEqual(dialog._chosen_databases(), ["Temp1", "Temp2"])
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
