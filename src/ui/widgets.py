"""Small widget helpers shared by tabs and dialogs (replaces parts of Helper.java)."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QPlainTextEdit, QRadioButton,
                               QStyledItemDelegate, QVBoxLayout, QWidget)


def lines(text: str) -> list[str]:
    """Split a multi-line text box into non-empty, trimmed lines."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def text_box(text: str = "", placeholder: str = "", rows: int = 4) -> QPlainTextEdit:
    box = QPlainTextEdit(text)
    box.setPlaceholderText(placeholder)
    box.setTabChangesFocus(True)  # Tab moves to the next field (replaces the Robot hack)
    box.setFixedHeight(box.fontMetrics().lineSpacing() * rows + 12)
    return box


def radio_group(enum_cls, selected=None) -> tuple[QWidget, QButtonGroup]:
    """One radio button per enum member, stacked vertically. First member selected by default."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    group = QButtonGroup(box)
    members = list(enum_cls)
    selected = selected if selected in members else members[0]
    for i, member in enumerate(members):
        button = QRadioButton(member.label)
        button.setChecked(member is selected)
        group.addButton(button, i)
        layout.addWidget(button)
    return box, group


def selected_member(enum_cls, group: QButtonGroup):
    return list(enum_cls)[max(group.checkedId(), 0)]


class CheckComboBox(QComboBox):
    """Dropdown of checkboxes; the popup stays open while ticking, the box shows the ticked names."""

    def __init__(self, items: list[str] = (), placeholder: str = "None selected"):
        super().__init__()
        self.setModel(QStandardItemModel(self))
        self.setItemDelegate(QStyledItemDelegate(self))  # the default combo delegate hides checkboxes
        self.setEditable(True)  # only so the box can show a comma list; typing is blocked below
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText(placeholder)
        self.lineEdit().installEventFilter(self)
        self.view().viewport().installEventFilter(self)
        self.view().installEventFilter(self)
        self.set_items(items)

    def set_items(self, items: list[str], checked: list[str] = ()) -> None:
        model: QStandardItemModel = self.model()
        model.clear()
        for text in items:
            item = QStandardItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if text in checked else Qt.CheckState.Unchecked)
            model.appendRow(item)
        self._refresh()

    def checked_items(self) -> list[str]:
        model: QStandardItemModel = self.model()
        return [model.item(i).text() for i in range(model.rowCount())
                if model.item(i).checkState() == Qt.CheckState.Checked]

    def hidePopup(self) -> None:
        super().hidePopup()
        self._refresh()  # QComboBox writes the "current" item into the box on close

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if obj is self.lineEdit() and kind == QEvent.Type.MouseButtonRelease and self.isEnabled():
            self.showPopup()
            return True
        if obj is self.view().viewport() and kind == QEvent.Type.MouseButtonRelease:
            self._toggle(self.view().indexAt(event.position().toPoint()))
            return True  # swallowed, so the popup doesn't close
        if (obj is self.view() and kind == QEvent.Type.KeyPress
                and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)):
            self._toggle(self.view().currentIndex())
            return True
        return super().eventFilter(obj, event)

    def _toggle(self, index) -> None:
        if not index.isValid():
            return
        item = self.model().itemFromIndex(index)
        checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)
        self._refresh()

    def _refresh(self) -> None:
        text = ", ".join(self.checked_items())
        self.lineEdit().setText(text)
        self.setToolTip(text)


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
