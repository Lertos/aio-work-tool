"""Qt adapter over ItemStore for QListView (replaces ObservableList + ListCell state)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import (QAbstractListModel, QByteArray, QMimeData, QModelIndex, Qt,
                            Signal)
from PySide6.QtGui import QColor

from ..config import TEXT_DONE
from .item_store import ItemStore
from .items import TodoItem

ItemRole = Qt.ItemDataRole.UserRole + 1
_MIME = "application/x-work-aio-row"


class ItemListModel(QAbstractListModel):
    historyChanged = Signal(bool)  # bind straight to undo_button.setVisible

    def __init__(self, store: ItemStore, tooltip: Callable[[object], str] | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self._tooltip = tooltip
        store.subscribe(lambda: self.historyChanged.emit(store.has_history))

    # ----------------------------------------------------------- read access
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.store)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.store[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.description
        if role == Qt.ItemDataRole.ToolTipRole and self._tooltip:
            return self._tooltip(item) or None
        if role == ItemRole:
            return item
        return None

    def flags(self, index):
        base = super().flags(index) | Qt.ItemFlag.ItemIsDragEnabled
        return base if index.isValid() else base | Qt.ItemFlag.ItemIsDropEnabled

    # ------------------------------------------------ mutations (use these)
    def add(self, item) -> None:
        row = len(self.store)
        self.beginInsertRows(QModelIndex(), row, row)
        self.store.add(item)
        self.endInsertRows()

    def replace(self, row: int, item) -> None:
        self.store.replace(row, item)
        idx = self.index(row)
        self.dataChanged.emit(idx, idx)

    def delete(self, row: int) -> None:
        self.beginRemoveRows(QModelIndex(), row, row)
        self.store.move_to_history(row)
        self.endRemoveRows()

    def undo_delete(self) -> None:
        if not self.store.has_history:
            return
        row = len(self.store)
        self.beginInsertRows(QModelIndex(), row, row)
        self.store.restore_last()
        self.endInsertRows()

    def delete_where(self, predicate) -> int:
        self.beginResetModel()
        count = self.store.remove_where(predicate)
        self.endResetModel()
        return count

    # --------------------------------------------- drag-and-drop (insert move)
    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [_MIME]

    def mimeData(self, indexes):
        mime = QMimeData()
        mime.setData(_MIME, QByteArray(str(indexes[0].row()).encode()))
        return mime

    def moveRows(self, src_parent, src_row, count, dst_parent, dst_row) -> bool:
        """Called by QListView for internal drags. ``dst_row`` is the insert position
        in the list *before* the source row is removed (Qt convention)."""
        if count != 1 or src_parent.isValid() or dst_parent.isValid():
            return False
        if dst_row in (src_row, src_row + 1):
            return False
        if not self.beginMoveRows(QModelIndex(), src_row, src_row, QModelIndex(), dst_row):
            return False
        self.store.move(src_row, dst_row - 1 if dst_row > src_row else dst_row)
        self.endMoveRows()
        return True

    def dropMimeData(self, mime, action, row, column, parent):
        """Fallback path if the view doesn't use moveRows."""
        if action != Qt.DropAction.MoveAction or not mime.hasFormat(_MIME):
            return False
        src = int(bytes(mime.data(_MIME)).decode())
        dest = row if row != -1 else (parent.row() if parent.isValid() else len(self.store))
        self.moveRows(QModelIndex(), src, 1, QModelIndex(), dest)
        return False  # we moved it ourselves; stop the view from also removing the source


class TodoModel(ItemListModel):
    """To-do rows get a native checkbox (drawn by the delegate) and grey text when done."""

    DONE_COLOR = QColor(TEXT_DONE)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            item: TodoItem = self.store[index.row()]
            if role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if item.done else Qt.CheckState.Unchecked
            if role == Qt.ItemDataRole.ForegroundRole:
                return self.DONE_COLOR if item.done else None  # None = theme's text colour
        return super().data(index, role)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole and index.isValid():
            self.store[index.row()].done = Qt.CheckState(value) == Qt.CheckState.Checked
            self.store.touch()
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
