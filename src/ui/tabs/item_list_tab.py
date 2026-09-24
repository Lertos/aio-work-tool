"""Shared layout and behaviour for every main-window tab (replaces the Controller* classes).

    QVBoxLayout
    ├── QListView            ItemListModel + ActionRowDelegate, drag to reorder
    ├── (extra widgets)      add_above_hint() hook - To-Do adds a separator
    ├── QLabel               hint
    ├── QHBoxLayout          centred buttons - build_buttons() hook
    └── QPushButton          Undo Delete, visible only while there is something to undo

Subclasses set TITLE / HINT and override open_editor(), and usually
on_row_clicked() and tooltip().
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QListView, QPushButton,
                               QVBoxLayout, QWidget)

from ...config import TAB_SPACING
from ...model.item_list_model import ItemListModel
from ...model.item_store import ItemStore
from ..delegates import ActionRowDelegate


class ItemListTab(QWidget):
    TITLE = ""
    HINT = ""
    SHOW_ROW_BUTTONS = True

    def __init__(self, store: ItemStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.model = self.create_model(store)

        self.view = QListView()
        self.view.setModel(self.model)
        self.view.setWordWrap(True)
        self.view.setUniformItemSizes(False)
        self.view.setResizeMode(QListView.ResizeMode.Adjust)  # re-wrap rows on resize
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.view.setDropIndicatorShown(True)

        self.delegate = ActionRowDelegate(self.view, show_actions=self.SHOW_ROW_BUTTONS)
        self.view.setItemDelegate(self.delegate)
        queued = Qt.ConnectionType.QueuedConnection
        self.delegate.rowClicked.connect(self._guard(self.on_row_clicked), queued)
        self.delegate.rowRightClicked.connect(self._guard(self.on_row_right_clicked), queued)
        self.delegate.editRequested.connect(self._guard(self.on_edit), queued)
        self.delegate.deleteRequested.connect(self._guard(self.on_delete), queued)

        self.hint_label = QLabel(self.HINT)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(TAB_SPACING)
        self.button_row.addStretch(1)
        self.build_buttons()
        self.button_row.addStretch(1)

        self.undo_button = QPushButton("Undo Delete")
        self.undo_button.clicked.connect(lambda: self.model.undo_delete())
        self.undo_button.setVisible(store.has_history)
        self.model.historyChanged.connect(self.undo_button.setVisible)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(TAB_SPACING, TAB_SPACING, TAB_SPACING, 10)
        layout.setSpacing(TAB_SPACING)
        layout.addWidget(self.view, 1)
        self.add_above_hint(layout)
        layout.addWidget(self.hint_label)
        layout.addLayout(self.button_row)
        layout.addWidget(self.undo_button, 0, Qt.AlignmentFlag.AlignHCenter)

    # ------------------------------------------------------------ hooks
    def create_model(self, store: ItemStore) -> ItemListModel:
        return ItemListModel(store, tooltip=self.tooltip)

    def tooltip(self, item) -> str:
        return ""

    def open_editor(self, item):
        """Show the add/edit dialog; return the new item or None if cancelled."""
        raise NotImplementedError

    def add_above_hint(self, layout: QVBoxLayout) -> None:
        pass

    def build_buttons(self) -> None:
        self.add_button("Add", self.on_add)

    def on_row_clicked(self, row: int) -> None:
        pass

    def on_row_right_clicked(self, row: int) -> None:
        self.on_edit(row)

    # ------------------------------------------------------------ actions
    def add_button(self, text: str, slot: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(lambda: slot())
        self.button_row.addWidget(button)
        return button

    def item(self, row: int):
        return self.model.store[row]

    def on_add(self) -> None:
        new = self.open_editor(None)
        if new is not None:
            self.model.add(new)
            self.view.scrollToBottom()

    def on_edit(self, row: int) -> None:
        new = self.open_editor(self.item(row))
        if new is not None:
            self.model.replace(row, new)

    def on_delete(self, row: int) -> None:
        self.model.delete(row)

    def _guard(self, slot: Callable[[int], None]) -> Callable[[int], None]:
        """Ignore a queued click whose row no longer exists."""
        def wrapper(row: int) -> None:
            if 0 <= row < len(self.model.store):
                slot(row)
        return wrapper
