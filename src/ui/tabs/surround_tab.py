"""Surround tab - click a row to wrap each clipboard line in its prefix/suffix."""
from __future__ import annotations

from PySide6.QtGui import QGuiApplication

from ...services.surround import surround
from ..dialogs.surround_dialog import SurroundDialog
from ..toast import show_toast
from .item_list_tab import ItemListTab


class SurroundTab(ItemListTab):
    TITLE = "Surround"
    HINT = "Click a row to surround each line on the clipboard"

    def tooltip(self, item) -> str:
        return f"Prefix: {item.prefix!r}\nSuffix: {item.suffix!r}"

    def open_editor(self, item):
        return SurroundDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        clipboard = QGuiApplication.clipboard()
        result = surround(clipboard.text(), self.item(row))
        if not result:
            show_toast(self, "Clipboard has no text")
            return
        clipboard.setText(result)
        count = result.count("\n") + 1
        show_toast(self, f"{count} line{'s' if count != 1 else ''} surrounded and copied")
