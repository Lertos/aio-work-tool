"""Queries tab - repeatable SQL Server queries; click one, pick a database, see the results."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from ...services.saved_query import QueryResult, run_query
from ..dialogs.query_results_dialog import QueryResultsDialog
from ..dialogs.saved_query_dialog import SavedQueryDialog
from ..worker import run_in_background
from .item_list_tab import ItemListTab


class SavedQueryTab(ItemListTab):
    TITLE = "Queries"
    HINT = "Click a query to run it against a database"
    _busy = False

    def tooltip(self, item) -> str:
        last = item.recent_databases[0] if item.recent_databases else "none yet"
        return f"{item.server} - last database: {last}\n\n{item.query[:500]}"

    def open_editor(self, item):
        return SavedQueryDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        if self._busy:
            return
        answer = SavedQueryDialog.ask(self, self.item(row), run=True)
        if answer is None:
            return  # cancelled - nothing is saved
        item, database = answer
        self.model.replace(row, item)  # keeps any edits and the last database used
        self._set_busy(True)
        run_in_background(lambda: run_query(item, database),
                          lambda result: self._on_done(f"{item.description} - {database}", result),
                          self._on_failed)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.view.setEnabled(not busy)
        self.hint_label.setText("Running…" if busy else self.HINT)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _on_done(self, title: str, result: QueryResult) -> None:
        self._set_busy(False)
        QueryResultsDialog(self, title, result).show()

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        QMessageBox.critical(self, self.TITLE, f"The query failed:\n\n{message}")
