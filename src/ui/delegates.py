"""List row painter + click router (replaces the per-tab *ItemCell classes).

Row layout, same as the Java HBox:   [checkbox?] wrapped text ......... [edit] [delete]

Signals carry the row number. Connect them with a QueuedConnection so the
model can safely add/remove rows after the mouse event has finished.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (QApplication, QListView, QStyle, QStyledItemDelegate,
                               QStyleOptionButton, QStyleOptionViewItem)

from ..config import DELETE_ICON, EDIT_ICON, ICON_SIZE, ROW_BUTTON_SIZE, ROW_MARGIN

_TEXT_FLAGS = (int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
               | int(Qt.TextFlag.TextWordWrap))

EDIT, DELETE, ROW = "edit", "delete", "row"


class ActionRowDelegate(QStyledItemDelegate):
    rowClicked = Signal(int)
    rowRightClicked = Signal(int)
    editRequested = Signal(int)
    deleteRequested = Signal(int)

    def __init__(self, view: QListView, show_actions: bool = True):
        super().__init__(view)
        self._view = view
        self._show_actions = show_actions
        self._sources = {EDIT: QPixmap(str(EDIT_ICON)), DELETE: QPixmap(str(DELETE_ICON))}
        self._icons: dict[tuple[str, int], QIcon] = {}  # (name, rgba) -> tinted icon
        self._pressed: tuple | None = None  # (row, region, button) of the current press

    def _icon(self, name: str, color: QColor) -> QIcon:
        """The icon recolored to ``color`` so it stays visible in both light and dark themes."""
        key = (name, color.rgba())
        if key not in self._icons:
            pixmap = QPixmap(self._sources[name])
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), color)  # keeps the alpha, replaces the color
            painter.end()
            self._icons[key] = QIcon(pixmap)
        return self._icons[key]

    # ---------------------------------------------------------------- geometry
    def _button_rects(self, rect: QRect) -> dict[str, QRect]:
        if not self._show_actions:
            return {}
        s = ROW_BUTTON_SIZE
        y = rect.top() + (rect.height() - s) // 2
        delete = QRect(rect.right() - ROW_MARGIN - s + 1, y, s, s)
        edit = QRect(delete.left() - ROW_MARGIN - s, y, s, s)
        return {EDIT: edit, DELETE: delete}

    def _style_option(self, option, index) -> QStyleOptionViewItem:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        return opt

    @staticmethod
    def _style(opt):
        return opt.widget.style() if opt.widget else QApplication.style()

    def _check_rect(self, opt: QStyleOptionViewItem) -> QRect | None:
        if not (opt.features & QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator):
            return None
        return self._style(opt).subElementRect(
            QStyle.SubElement.SE_ItemViewItemCheckIndicator, opt, opt.widget)

    def _text_rect(self, opt: QStyleOptionViewItem) -> QRect:
        rect = opt.rect.adjusted(ROW_MARGIN, ROW_MARGIN, -ROW_MARGIN, -ROW_MARGIN)
        check = self._check_rect(opt)
        if check is not None:
            rect.setLeft(check.right() + ROW_MARGIN + 2)
        buttons = self._button_rects(opt.rect)
        if buttons:
            rect.setRight(buttons[EDIT].left() - ROW_MARGIN)
        return rect

    def _region(self, rect: QRect, pos) -> str:
        for name, button in self._button_rects(rect).items():
            if button.contains(pos):
                return name
        return ROW

    # ---------------------------------------------------------------- painting
    def paint(self, painter, option, index):
        opt = self._style_option(option, index)
        text = opt.text
        opt.text = ""
        style = self._style(opt)
        # Background, selection highlight, focus rect and checkbox - but no text.
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        painter.save()
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        painter.setPen(opt.palette.color(role))
        painter.setFont(opt.font)
        painter.drawText(self._text_rect(opt), _TEXT_FLAGS, text)
        painter.restore()

        for name, rect in self._button_rects(opt.rect).items():
            button = QStyleOptionButton()
            button.rect = rect
            button.icon = self._icon(name, opt.palette.color(QPalette.ColorRole.ButtonText))
            button.iconSize = QSize(ICON_SIZE, ICON_SIZE)
            button.state = QStyle.StateFlag.State_Enabled
            if self._pressed and self._pressed[:2] == (index.row(), name):
                button.state |= QStyle.StateFlag.State_Sunken
            else:
                button.state |= QStyle.StateFlag.State_Raised
            style.drawControl(QStyle.ControlElement.CE_PushButton, button, painter, opt.widget)

    def sizeHint(self, option, index):
        opt = self._style_option(option, index)
        width = max(self._view.viewport().width(), 50)
        min_height = ROW_BUTTON_SIZE if self._show_actions else opt.fontMetrics.height()
        opt.rect = QRect(0, 0, width, min_height + 2 * ROW_MARGIN)
        text_width = max(self._text_rect(opt).width(), 20)
        text_height = opt.fontMetrics.boundingRect(
            QRect(0, 0, text_width, 100_000), _TEXT_FLAGS, opt.text).height()
        return QSize(width, max(text_height, min_height) + 2 * ROW_MARGIN)

    # ------------------------------------------------------------------ clicks
    def editorEvent(self, event, model, option, index):
        kind = event.type()
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return super().editorEvent(event, model, option, index)

        pos = event.position().toPoint()
        opt = self._style_option(option, index)
        check = self._check_rect(opt)
        if check is not None and check.contains(pos):
            return super().editorEvent(event, model, option, index)  # built-in toggle

        region = self._region(option.rect, pos)
        key = (index.row(), region, event.button())

        if kind == QEvent.Type.MouseButtonPress:
            self._pressed = key
            self._view.viewport().update(option.rect)
            # Swallow presses on the buttons so they don't select the row or start a drag.
            return region != ROW

        pressed, self._pressed = self._pressed, None
        self._view.viewport().update(option.rect)
        if pressed != key:
            return False  # press and release were on different targets - not a click
        row = index.row()
        if event.button() == Qt.MouseButton.LeftButton:
            {EDIT: self.editRequested, DELETE: self.deleteRequested,
             ROW: self.rowClicked}[region].emit(row)
        elif event.button() == Qt.MouseButton.RightButton and region == ROW:
            self.rowRightClicked.emit(row)
        return region != ROW
