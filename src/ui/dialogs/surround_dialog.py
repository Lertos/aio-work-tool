"""Add/edit dialog for the Surround tab."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLineEdit

from ...model.items import SurroundItem
from .item_form_dialog import ItemFormDialog, ValidationError


class SurroundDialog(ItemFormDialog):
    def __init__(self, parent, item: SurroundItem | None = None):
        super().__init__(parent, *(("Edit Surround", "Update") if item else ("Add Surround", "Add")))
        self.prefix = QLineEdit(item.prefix if item else "")
        self.suffix = QLineEdit(item.suffix if item else "")
        self.remove_final = QCheckBox("Remove final suffix")
        self.remove_final.setChecked(item.remove_final_suffix if item else False)
        self.remove_final.setToolTip("Drop the trailing , or ; from the last line's suffix,\n"
                                     "e.g. suffix ', gives 'a', 'b', 'c'")

        self.form.addRow("Prefix", self.prefix)
        self.form.addRow("Suffix", self.suffix)
        self.form.addRow("", self.remove_final)
        self.resize(420, self.sizeHint().height())

    def validate(self) -> None:
        if not self.prefix.text() and not self.suffix.text():
            raise ValidationError("Enter a prefix, a suffix, or both")

    def build_result(self) -> SurroundItem:
        # Not stripped: spaces in the prefix/suffix may be intentional.
        return SurroundItem(self.prefix.text(), self.suffix.text(), self.remove_final.isChecked())
