from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from ...services.sql_compare import CompareReport, compare
from ..dialogs.sql_compare_dialog import SqlCompareDialog
from ..dialogs.sql_compare_run_dialog import SqlCompareRunDialog
from ..worker import run_in_background
from .item_list_tab import ItemListTab


class SqlCompareTab(ItemListTab):
    TITLE = "SQL Compare"
    HINT = "Click a row to compare the procedure across servers"
    _busy = False

    def tooltip(self, item) -> str:
        servers = ", ".join(s.tab_name for s in item.servers) or "no servers"
        return f"{item.procedure_name} on {servers}"

    def open_editor(self, item):
        return SqlCompareDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        if self._busy:
            return
        run = SqlCompareRunDialog.ask(self, self.item(row))
        if run is None:
            return
        self._set_busy(True)
        run_in_background(lambda: compare(run), self._on_done, self._on_failed)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.view.setEnabled(not busy)
        self.hint_label.setText("Comparing…" if busy else self.HINT)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _on_done(self, report: CompareReport) -> None:
        self._set_busy(False)
        show = QMessageBox.information if report.all_match else QMessageBox.warning
        show(self, self.TITLE, report.summary())

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        QMessageBox.critical(self, self.TITLE, f"The comparison failed:\n\n{message}")
