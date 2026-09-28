"""Add/edit dialogs for the To-Do, Info, Scripts, Copy and Folders tabs."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget

from ...model.items import CopyItem, FolderItem, InfoItem, ScriptItem, TodoItem
from ..widgets import text_box
from .item_form_dialog import ItemFormDialog, ValidationError


def _titles(noun: str, item) -> tuple[str, str]:
    return (f"Edit {noun}", "Update") if item else (f"Add {noun}", "Add")


class _DescriptionDialog(ItemFormDialog):
    """Display Text line + one multi-line field; shared by To-Do, Info, Scripts and Copy."""

    NOUN = ""
    TEXT_LABEL = ""
    TEXT_REQUIRED = False
    TEXT_ROWS = 4

    def __init__(self, parent, item=None):
        super().__init__(parent, *_titles(self.NOUN, item))
        self._item = item
        self.name = QLineEdit(item.description if item else "")
        self.text = text_box(self._text_of(item) if item else "", rows=self.TEXT_ROWS)
        self.form.addRow("Display Text", self.name)
        self.form.addRow(self.TEXT_LABEL, self.text)
        self.resize(420, self.sizeHint().height())

    def validate(self) -> None:
        if not self.name.text().strip():
            raise ValidationError("'Display Text' cannot be empty")
        if self.TEXT_REQUIRED and not self.text.toPlainText().strip():
            raise ValidationError(f"'{self.TEXT_LABEL}' cannot be empty")

    def _text_of(self, item) -> str:
        raise NotImplementedError


class TodoDialog(_DescriptionDialog):
    NOUN, TEXT_LABEL = "To-Do", "Additional Text"

    def _text_of(self, item: TodoItem) -> str:
        return item.additional_text

    def build_result(self) -> TodoItem:
        return TodoItem(self.name.text().strip(), self.text.toPlainText().strip(),
                        done=self._item.done if self._item else False)


class InfoDialog(_DescriptionDialog):
    NOUN, TEXT_LABEL = "Info", "Additional Text"

    def _text_of(self, item: InfoItem) -> str:
        return item.additional_text

    def build_result(self) -> InfoItem:
        return InfoItem(self.name.text().strip(), self.text.toPlainText().strip())


class ScriptDialog(_DescriptionDialog):
    NOUN, TEXT_LABEL, TEXT_REQUIRED, TEXT_ROWS = "Script", "PowerShell Commands", True, 10

    def __init__(self, parent, item: ScriptItem | None = None):
        super().__init__(parent, item)
        self.text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.text.setPlaceholderText("One command per line, like a batch file, e.g.\n"
                                     "Set-Location C:\\Projects\\app\n"
                                     "git pull\n"
                                     "npm run build")
        self.elevated = QCheckBox()
        self.elevated.setChecked(bool(item and item.run_as_admin))
        self.elevated.setToolTip("Run as administrator - Windows will ask for permission first")
        self.form.addRow("Needs Elevated Access", self.elevated)
        self.resize(560, self.sizeHint().height())

    def _text_of(self, item: ScriptItem) -> str:
        return item.commands

    def build_result(self) -> ScriptItem:
        return ScriptItem(self.name.text().strip(), self.text.toPlainText().strip(),
                          self.elevated.isChecked())


class CopyDialog(_DescriptionDialog):
    NOUN, TEXT_LABEL, TEXT_REQUIRED = "Copy Text", "Text To Copy", True

    def _text_of(self, item: CopyItem) -> str:
        return item.text_to_copy

    def build_result(self) -> CopyItem:
        # Not stripped: leading/trailing whitespace may matter in copied text.
        return CopyItem(self.name.text().strip(), self.text.toPlainText())


class FolderDialog(ItemFormDialog):
    def __init__(self, parent, item: FolderItem | None = None):
        super().__init__(parent, *_titles("Folder", item))
        self.name = QLineEdit(item.description if item else "")
        self.path = QLineEdit(item.path_to_open if item else "")
        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Choose a folder")
        browse.clicked.connect(self._browse)
        path_row = QWidget()
        row = QHBoxLayout(path_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        self.check_exists = QCheckBox()
        self.check_exists.setChecked(True)

        self.form.addRow("Display Text", self.name)
        self.form.addRow("Path to Open", path_row)
        self.form.addRow("Check Path Exists", self.check_exists)
        self.resize(420, self.sizeHint().height())

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder", self.path.text())
        if folder:
            self.path.setText(str(Path(folder)))
            if not self.name.text().strip():
                self.name.setText(Path(folder).name)

    def validate(self) -> None:
        if not self.name.text().strip():
            raise ValidationError("'Display Text' cannot be empty")
        path = self.path.text().strip()
        if not path:
            raise ValidationError("'Path to Open' cannot be empty")
        if self.check_exists.isChecked() and not Path(path).is_dir():
            raise ValidationError("The given path does not exist")

    def build_result(self) -> FolderItem:
        return FolderItem(self.name.text().strip(), self.path.text().strip())
