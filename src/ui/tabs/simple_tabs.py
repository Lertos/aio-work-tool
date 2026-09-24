"""Folders, Copy and Info tabs - each is a few overrides on ItemListTab."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QMessageBox

from ..dialogs.simple_dialogs import CopyDialog, FolderDialog, InfoDialog
from ..toast import show_toast
from .item_list_tab import ItemListTab


class FoldersTab(ItemListTab):
    TITLE = "Folders"
    HINT = "Click a row to open the folder"

    def tooltip(self, item) -> str:
        return item.path_to_open

    def open_editor(self, item):
        return FolderDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        path = Path(self.item(row).path_to_open)
        if not path.is_dir():
            QMessageBox.warning(self, self.TITLE, f"The folder does not exist:\n{path}")
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, self.TITLE, f"The folder could not be opened:\n{path}")


class CopyTab(ItemListTab):
    TITLE = "Copy"
    HINT = "Click a row to copy the text"

    def tooltip(self, item) -> str:
        return item.text_to_copy

    def open_editor(self, item):
        return CopyDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        QGuiApplication.clipboard().setText(self.item(row).text_to_copy)
        show_toast(self, "Text copied to clipboard")


class InfoTab(ItemListTab):
    TITLE = "Info"
    HINT = "Click a row to view or edit it"

    def tooltip(self, item) -> str:
        return item.additional_text

    def open_editor(self, item):
        return InfoDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        self.on_edit(row)
