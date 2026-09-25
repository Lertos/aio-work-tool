"""Schema Backup tab - each row is a SQL Server environment; click one to back up definitions."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from ...services.schema_backup import BackupResult, backup
from ..dialogs.schema_backup_dialog import SchemaEnvironmentDialog
from ..dialogs.schema_backup_run_dialog import SchemaBackupRunDialog
from ..worker import run_in_background
from .item_list_tab import ItemListTab


class SchemaBackupTab(ItemListTab):
    TITLE = "Schema Backup"
    HINT = "Click an environment to back up procedures, functions and triggers"
    _busy = False

    def tooltip(self, item) -> str:
        return f"{item.server}\n{', '.join(item.databases) or 'no saved databases'}"

    def open_editor(self, item):
        return SchemaEnvironmentDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        if self._busy:
            return
        env = self.item(row)
        request = SchemaBackupRunDialog.ask(self, env)
        if request is None:
            return
        self._set_busy(True)
        run_in_background(
            lambda: backup(env, request.databases, request.entities, request.save_to),
            self._on_done, self._on_failed)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.view.setEnabled(not busy)
        self.hint_label.setText("Backing up…" if busy else self.HINT)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _on_done(self, result: BackupResult) -> None:
        self._set_busy(False)
        problems = bool(result.missing or result.errors)
        box = QMessageBox(QMessageBox.Icon.Warning if problems else QMessageBox.Icon.Information,
                          self.TITLE, result.summary(), parent=self)
        open_button = box.addButton("Open Folder", QMessageBox.ButtonRole.AcceptRole) \
            if result.saved else None
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if open_button is not None and box.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(result.folder)))

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        QMessageBox.critical(self, self.TITLE, f"The backup failed:\n\n{message}")
