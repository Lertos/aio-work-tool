"""Add/edit an environment for the Schema Backup tab."""
from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import QLineEdit

from ...model.items import SchemaEnvironment
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
        self.server = QLineEdit(item.server if item else "")
        self.server.setPlaceholderText(r"e.g. SQLPROD01 or SQLPROD01\INSTANCE,1433")
        self.connection = QLineEdit(item.connection_string if item else "")
        self.connection.setPlaceholderText("Optional, e.g. UID=me;PWD=secret;TrustServerCertificate=yes")
        self.connection.setToolTip(
            "Extra ODBC settings, or a full connection string.\n"
            "Blank = Windows login. Driver, Server and Database are filled in for you.\n"
            "Stored in Windows Credential Manager, not in the app's data files.")
        self.databases = text_box("\n".join(item.databases) if item else "",
                                  "One per line - these fill the database dropdown", rows=5)

        self.form.addRow("Display Text", self.name)
        self.form.addRow("Server Name", self.server)
        self.form.addRow("Connection String", self.connection)
        self.form.addRow("Databases", self.databases)
        self.resize(480, self.sizeHint().height())

    def validate(self) -> None:
        if not self.server.text().strip():
            raise ValidationError("'Server Name' cannot be empty")

    def build_result(self) -> SchemaEnvironment:
        values = dict(description=self.name.text().strip() or self.server.text().strip(),
                      server=self.server.text().strip(),
                      databases=split_names(self.databases.toPlainText()),
                      connection_string=self.connection.text().strip())
        if self._item:  # keep the id so the stored connection string stays linked
            return dataclasses.replace(self._item, **values)
        return SchemaEnvironment(**values)
