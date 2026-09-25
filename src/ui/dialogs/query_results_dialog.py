"""Non-modal window showing a query's result sets as tables (Queries tab).

Ctrl+C copies the selected cells and "Copy All" copies the current table with
its headers, both tab-separated so they paste straight into Excel.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QTableView, QTabWidget, QVBoxLayout)

from ...config import SPACING, TEXT_DONE
from ...services.saved_query import MAX_ROWS, QueryResult, ResultSet
from ..toast import show_toast


def format_cell(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "0x" + bytes(value).hex().upper()
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="milliseconds" if value.microsecond else "seconds")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def to_tsv(rows: list[list[str]]) -> str:
    """Tab-separated text; tabs/newlines inside a cell become spaces so Excel keeps the grid."""
    clean = lambda s: s.replace("\t", " ").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return "\n".join("\t".join(clean(cell) for cell in row) for row in rows)


class ResultTableModel(QAbstractTableModel):
    def __init__(self, result: ResultSet, parent=None):
        super().__init__(parent)
        self.result = result

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.result.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.result.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self.result.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return format_cell(value)
        if role == Qt.ItemDataRole.ForegroundRole and value is None:
            return QGuiApplication.palette().placeholderText()
        if role == Qt.ItemDataRole.TextAlignmentRole and isinstance(value, (int, float, Decimal)) \
                and not isinstance(value, bool):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.result.columns[section]
        return str(section + 1)

    def as_rows(self, cells: list[QModelIndex] | None = None, headers: bool = False) -> list[list[str]]:
        """All rows, or just the rectangle covering ``cells``."""
        if cells is None:
            rows, cols = range(self.rowCount()), range(self.columnCount())
        else:
            rows = sorted({i.row() for i in cells})
            cols = sorted({i.column() for i in cells})
        out = [[self.result.columns[c] for c in cols]] if headers else []
        selected = None if cells is None else {(i.row(), i.column()) for i in cells}
        for r in rows:
            out.append([format_cell(self.result.rows[r][c])
                        if selected is None or (r, c) in selected else "" for c in cols])
        return out


class QueryResultsDialog(QDialog):
    def __init__(self, parent, title: str, result: QueryResult):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint)
        self._views: list[QTableView] = []

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        for i, result_set in enumerate(result.result_sets, 1):
            self.tabs.addTab(self._table(result_set), f"Result {i} ({len(result_set.rows):,})")
        self.tabs.tabBar().setVisible(len(result.result_sets) > 1)

        info = list(result.messages)
        if any(rs.truncated for rs in result.result_sets):
            info.append(f"Only the first {MAX_ROWS:,} rows of a result are shown.")
        if not result.result_sets and not info:
            info.append("The query finished and returned no results.")
        self.info = QLabel("\n".join(info))
        self.info.setWordWrap(True)
        self.info.setStyleSheet(f"color: {TEXT_DONE};")
        self.info.setVisible(bool(info))

        copy_all = QPushButton("Copy All")
        copy_all.setToolTip("Copy the current table with its headers (pastes into Excel)")
        copy_all.clicked.connect(self._copy_all)
        copy_all.setEnabled(bool(result.result_sets))
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(copy_all)
        buttons.addWidget(close)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        layout.setSpacing(SPACING)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.info)
        layout.addLayout(buttons)
        self.tabs.setVisible(bool(result.result_sets))
        self.resize(800, 500 if result.result_sets else 150)

    def _table(self, result_set: ResultSet) -> QTableView:
        view = QTableView()
        view.setModel(ResultTableModel(result_set, view))
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setAlternatingRowColors(True)
        view.setWordWrap(False)
        view.verticalHeader().setDefaultSectionSize(view.fontMetrics().height() + 8)
        view.resizeColumnsToContents()
        for c in range(view.model().columnCount()):  # keep one long column from taking over
            view.setColumnWidth(c, min(view.columnWidth(c), 400))
        QShortcut(QKeySequence.StandardKey.Copy, view, lambda v=view: self._copy_selection(v))
        self._views.append(view)
        return view

    def _copy_selection(self, view: QTableView) -> None:
        cells = view.selectionModel().selectedIndexes()
        if cells:
            QGuiApplication.clipboard().setText(to_tsv(view.model().as_rows(cells)))

    def _copy_all(self) -> None:
        view = self._views[self.tabs.currentIndex()]
        QGuiApplication.clipboard().setText(to_tsv(view.model().as_rows(headers=True)))
        show_toast(self, "Copied")
