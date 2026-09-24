from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from ...model.items import PromoteType
from ...services import promoter
from ..dialogs.promote_dialog import Mode, PromoteDialog
from ..toast import show_toast
from .item_list_tab import ItemListTab


class PromoterTab(ItemListTab):
    TITLE = "Promoter"
    HINT = "Click a row to open the promoter window"

    def tooltip(self, item) -> str:
        verb = "Move" if item.promote_type is PromoteType.MOVE else "Copy"
        return f"{verb}: {', '.join(item.file_names) or '(choose files each time)'}"

    def build_buttons(self) -> None:
        self.add_button("Add", self.on_add)
        self.add_button("One Off", lambda: self.run(None))

    def open_editor(self, item):
        return PromoteDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        self.run(self.item(row))

    def run(self, stored) -> None:
        item = PromoteDialog.ask(self, stored, mode=Mode.RUN)
        if item is None:
            return  # cancelled - never re-runs a previous promotion
        problems = promoter.validate(item)
        if problems:
            QMessageBox.warning(self, "Promote", "Nothing was promoted:\n\n" + "\n".join(problems))
            return
        result = promoter.promote(item)
        if result.errors:
            QMessageBox.warning(
                self, "Promote",
                f"{len(result.promoted)} file(s) promoted, {len(result.errors)} failed:\n\n"
                + "\n".join(result.errors))
        else:
            show_toast(self, f"{len(result.promoted)} file(s) promoted")
