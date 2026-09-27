"""Add/edit a saved query, or run it (same form plus a Database box at the top)."""
from __future__ import annotations

import dataclasses

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QComboBox, QLineEdit

from ...model.items import SavedQuery
from ...services.odbc import server_from
from ...services.saved_query import remember_database
from ..widgets import text_box
from .item_form_dialog import ItemFormDialog, ValidationError


def _default_description(query: str) -> str:
    first = next((ln.strip() for ln in query.splitlines() if ln.strip()), "Query")
    return first if len(first) <= 60 else first[:57] + "…"


class SavedQueryDialog(ItemFormDialog):
    """Edit mode returns a SavedQuery. Run mode returns (updated SavedQuery, database)."""

    def __init__(self, parent, item: SavedQuery | None = None, run: bool = False):
        if run:
            title, accept = f"Run - {item.description}", "Run"
        else:
            title, accept = ("Edit Query", "Update") if item else ("Add Query", "Add")
        super().__init__(parent, title, accept)
        self._item, self._run = item, run

        self.database = QComboBox()
        self.database.setEditable(True)
        self.database.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if item:
            self.database.addItems(item.recent_databases)  # last used is first, so it's selected
        self.database.lineEdit().setPlaceholderText("Database to run against")

        self.name = QLineEdit(item.description if item else "")
        self.name.setPlaceholderText("Optional - defaults to the first line of the query")
        self.connection = QLineEdit(item.connection_string if item else "")
        self.connection.setPlaceholderText("e.g. Server=SQLPROD01;UID=me;PWD=secret;TrustServerCertificate=yes")
        self.connection.setToolTip(
            "ODBC connection string - must include Server=...\n"
            "No login given = Windows login. Driver and Database are filled in for you.\n"
            "Stored in Windows Credential Manager, not in the app's data files.")
        self.query = text_box(item.query if item else "", "SELECT ...\n\nGO on its own line "
                                                          "separates batches", rows=12)
        self.query.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

        if run:
            self.form.addRow("Database", self.database)
        self.form.addRow("Display Text", self.name)
        self.form.addRow("Connection String", self.connection)
        self.form.addRow("Query", self.query)
        self.resize(620, self.sizeHint().height())
        (self.database if run else self.name).setFocus()

    def validate(self) -> None:
        if self._run and not self.database.currentText().strip():
            raise ValidationError("Enter a database to run against")
        if not server_from(self.connection.text()):
            raise ValidationError("'Connection String' must include Server=...")
        if not self.query.toPlainText().strip():
            raise ValidationError("'Query' cannot be empty")

    def build_result(self):
        query = self.query.toPlainText().strip()
        values = dict(description=self.name.text().strip() or _default_description(query),
                      query=query,
                      connection_string=self.connection.text().strip())
        item = dataclasses.replace(self._item, **values) if self._item else SavedQuery(**values)
        if not self._run:
            return item
        database = self.database.currentText().strip()
        return dataclasses.replace(item, recent_databases=remember_database(item, database)), database
