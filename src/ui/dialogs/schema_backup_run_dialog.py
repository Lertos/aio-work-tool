"""Pick the entities and databases for one schema backup run."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget

from ...model.items import SchemaEnvironment
from ...services.schema_backup import split_names
from ..widgets import CheckComboBox, text_box
from .item_form_dialog import ItemFormDialog, ValidationError

_SAVE_TO_KEY = "schema_backup/save_to"


@dataclass
class BackupRequest:
    databases: list[str]
    entities: list[str]
    save_to: Path


def _default_save_to() -> str:
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return str(Path(documents) / "Schema Backups")


class SchemaBackupRunDialog(ItemFormDialog):
    def __init__(self, parent, env: SchemaEnvironment):
        super().__init__(parent, f"Schema Backup - {env.description}", "Back Up")
        server = QLineEdit(env.server)
        server.setReadOnly(True)
        self.entities = text_box("", "Procedures, functions, triggers or views - one per line\n"
                                     "e.g. dbo.usp_GetOrders", rows=7)
        self.databases = CheckComboBox(env.databases, "Choose databases")
        if len(env.databases) == 1:
            self.databases.set_items(env.databases, checked=env.databases)
        self.manual = text_box("", "Optional - one per line. Used instead of the dropdown "
                                   "for this run only", rows=3)
        self.manual.textChanged.connect(self._on_manual_changed)

        self.save_to = QLineEdit(QSettings().value(_SAVE_TO_KEY, _default_save_to()))
        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Choose a folder")
        browse.clicked.connect(self._browse)
        save_row = QWidget()
        row = QHBoxLayout(save_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.save_to, 1)
        row.addWidget(browse)

        self.form.addRow("Server", server)
        self.form.addRow("Entities", self.entities)
        self.form.addRow("Databases", self.databases)
        self.form.addRow("Or These Databases", self.manual)
        self.form.addRow("Save To", save_row)
        self.resize(500, self.sizeHint().height())
        self.entities.setFocus()

    def _on_manual_changed(self) -> None:
        # Typed databases replace the dropdown, so grey it out to make that obvious.
        self.databases.setEnabled(not split_names(self.manual.toPlainText()))

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Save backups to", self.save_to.text())
        if folder:
            self.save_to.setText(str(Path(folder)))

    def _chosen_databases(self) -> list[str]:
        return split_names(self.manual.toPlainText()) or self.databases.checked_items()

    def validate(self) -> None:
        if not split_names(self.entities.toPlainText()):
            raise ValidationError("Enter at least one entity name")
        if not self._chosen_databases():
            raise ValidationError("Choose at least one database, or type some in "
                                  "'Or These Databases'")
        if not self.save_to.text().strip():
            raise ValidationError("'Save To' cannot be empty")

    def build_result(self) -> BackupRequest:
        save_to = self.save_to.text().strip()
        QSettings().setValue(_SAVE_TO_KEY, save_to)
        return BackupRequest(self._chosen_databases(), split_names(self.entities.toPlainText()),
                             Path(save_to))
