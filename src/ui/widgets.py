"""Small widget helpers shared by tabs and dialogs (replaces parts of Helper.java)."""
from __future__ import annotations

from PySide6.QtWidgets import (QButtonGroup, QFrame, QPlainTextEdit, QRadioButton,
                               QVBoxLayout, QWidget)


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


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
