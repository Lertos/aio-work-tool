"""One dialog for both PromotePopup (add/edit) and PromoteRunPopup (run / one-off)."""
from __future__ import annotations

from enum import Enum, auto

from PySide6.QtWidgets import QLineEdit

from ...model.items import PathType, PromoteItem, PromoteType
from ..widgets import lines, radio_group, selected_member, text_box
from .item_form_dialog import ItemFormDialog, ValidationError


class Mode(Enum):
    ADD = auto()
    EDIT = auto()
    RUN = auto()


_TITLES = {Mode.ADD: ("Add Promotion", "Add"), Mode.EDIT: ("Edit Promotion", "Update"),
           Mode.RUN: ("Run Promotion", "Promote")}


class PromoteDialog(ItemFormDialog):
    def __init__(self, parent, item: PromoteItem | None = None, mode: Mode | None = None):
        mode = mode or (Mode.EDIT if item else Mode.ADD)
        title, accept = _TITLES[mode]
        super().__init__(parent, title, accept)
        self.mode = mode
        src = item or PromoteItem(description="One off" if mode is Mode.RUN else "")

        self.name = QLineEdit(src.description)
        self.name.setReadOnly(mode is Mode.RUN)
        path_box, self.path_group = radio_group(PathType, src.path_type)
        type_box, self.type_group = radio_group(PromoteType, src.promote_type)
        hint = "" if mode is Mode.RUN else "Leave blank to fill in each time"
        self.files = text_box("\n".join(src.file_names), hint, rows=3)
        self.origins = text_box("\n".join(src.origin_paths), hint, rows=3)
        self.destinations = text_box("\n".join(src.destination_paths), hint, rows=3)

        self.form.addRow("Display Text", self.name)
        self.form.addRow("Path Type", path_box)
        self.form.addRow("Promote Type", type_box)
        self.form.addRow("Files To Promote\n(1 per line)", self.files)
        self.form.addRow("Origin Paths\n(1 per line)", self.origins)
        self.form.addRow("Destination Paths\n(1 per line)", self.destinations)
        self.resize(480, self.sizeHint().height())

    def validate(self) -> None:
        if not self.name.text().strip():
            raise ValidationError("'Display Text' cannot be empty")
        if self.mode is Mode.RUN:
            if not lines(self.origins.toPlainText()):
                raise ValidationError("Enter at least one origin path")
            if not lines(self.destinations.toPlainText()):
                raise ValidationError("Enter at least one destination path")
            if (selected_member(PathType, self.path_group) is PathType.FILE_NAMES_SEPARATE
                    and not lines(self.files.toPlainText())):
                raise ValidationError("Enter at least one file to promote")

    def build_result(self) -> PromoteItem:
        return PromoteItem(
            description=self.name.text().strip(),
            path_type=selected_member(PathType, self.path_group),
            promote_type=selected_member(PromoteType, self.type_group),
            file_names=lines(self.files.toPlainText()),
            origin_paths=lines(self.origins.toPlainText()),
            destination_paths=lines(self.destinations.toPlainText()),
        )
