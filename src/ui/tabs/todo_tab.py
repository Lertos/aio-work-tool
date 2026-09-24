from __future__ import annotations

from ...config import TEXT_ERROR
from ...model.item_list_model import TodoModel
from ..dialogs.simple_dialogs import TodoDialog
from ..widgets import hline
from .item_list_tab import ItemListTab


class TodoTab(ItemListTab):
    TITLE = "To-Do"
    SHOW_ROW_BUTTONS = False  # checkbox instead; edit = right-click, delete = delete mode
    HINT_EDIT = "To EDIT, right-click the text of a row"
    HINT_DELETE = "To DELETE, click the text of a row"
    delete_mode = False

    def __init__(self, store, parent=None):
        super().__init__(store, parent)
        self.set_delete_mode(False)

    def create_model(self, store):
        return TodoModel(store, tooltip=lambda item: item.additional_text)

    def add_above_hint(self, layout) -> None:
        layout.addWidget(hline())

    def build_buttons(self) -> None:
        self.btn_delete_multiple = self.add_button("Delete Multiple",
                                                   lambda: self.set_delete_mode(True))
        self.btn_delete_checked = self.add_button("Delete Checked", self.delete_checked)
        self.btn_add = self.add_button("Add", self.on_add)
        self.btn_finish = self.add_button("Finish Deleting", lambda: self.set_delete_mode(False))

    def set_delete_mode(self, enabled: bool) -> None:
        self.delete_mode = enabled
        self.hint_label.setText(self.HINT_DELETE if enabled else self.HINT_EDIT)
        self.hint_label.setStyleSheet(f"color: {TEXT_ERROR};" if enabled else "")
        for button in (self.btn_delete_multiple, self.btn_delete_checked, self.btn_add):
            button.setVisible(not enabled)
        self.btn_finish.setVisible(enabled)

    def delete_checked(self) -> None:
        self.model.delete_where(lambda item: item.done)

    def open_editor(self, item):
        return TodoDialog.ask(self, item)

    def on_row_clicked(self, row: int) -> None:
        if self.delete_mode:
            self.on_delete(row)

    def on_row_right_clicked(self, row: int) -> None:
        if not self.delete_mode:
            self.on_edit(row)
