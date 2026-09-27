"""Add/edit an environment for the Schema Backup tab."""
from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import QLineEdit

from ...model.items import SchemaEnvironment
from ...services.odbc import server_from
from ...services.schema_backup import split_names
from ..widgets import text_box
from .item_form_dialog import ItemFormDialog, ValidationError


class SchemaEnvironmentDialog(ItemFormDialog):
    def __init__(self, parent, item: SchemaEnvironment | None = None):
        super().__init__(parent, *(("Edit Environment", "Update") if item
                                   else ("Add Environment", "Add")))
        self._item = item
        self.name = QLineEdit(item.description if item else "")
        self.name.setPlaceholderText("Optional, e.g. Prod - defaults to the server name")
        self.connection = QLineEdit(item.connection_string if item else "")
        self.connection.setPlaceholderText("e.g. Server=SQLPROD01;UID=me;PWD=secret;TrustServerCertificate=yes")
        self.connection.setToolTip(
            "ODBC connection string - must include Server=...\n"
            "No login given = Windows login. Driver and Database are filled in for you.\n"
            "Stored in Windows Credential Manager, not in the app's data files.")
        self.databases = text_box("\n".join(item.databases) if item else "",
                                  "One per line - these fill the database dropdown", rows=5)

        self.form.addRow("Display Text", self.name)
        self.form.addRow("Connection String", self.connection)
        self.form.addRow("Databases", self.databases)
        self.resize(480, self.sizeHint().height())

    def validate(self) -> None:
        if not server_from(self.connection.text()):
            raise ValidationError("'Connection String' must include Server=...")

    def build_result(self) -> SchemaEnvironment:
        connection = self.connection.text().strip()
        values = dict(description=self.name.text().strip() or server_from(connection),
                      databases=split_names(self.databases.toPlainText()),
                      connection_string=connection)
        if self._item:  # keep the id so the stored connection string stays linked
            return dataclasses.replace(self._item, **values)
        return SchemaEnvironment(**values)
