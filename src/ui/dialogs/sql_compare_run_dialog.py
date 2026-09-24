"""Confirm/adjust the procedure name and databases before a compare (was SQLCompareRunPopup)."""
from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import QFormLayout, QLineEdit, QTabWidget, QWidget

from ...config import SPACING
from ...model.items import SQLCompareItem
from ..widgets import hline, lines, text_box
from .item_form_dialog import ItemFormDialog, ValidationError


class _RunServerPage(QWidget):
    def __init__(self, host: str, databases: list[str]):
        super().__init__()
        form = QFormLayout(self)
        form.setHorizontalSpacing(SPACING)
        form.setVerticalSpacing(SPACING)
        host_edit = QLineEdit(host)
        host_edit.setReadOnly(True)
        self.databases = text_box("\n".join(databases), "Each line is a new database", rows=3)
        form.addRow("Host", host_edit)
        form.addRow("Databases", self.databases)


class SqlCompareRunDialog(ItemFormDialog):
    """Returns a *copy* of the item with the run-time edits; the saved item is untouched."""

    def __init__(self, parent, item: SQLCompareItem):
        super().__init__(parent, f"Compare - {item.description}", "Compare")
        self._item = item
        name = QLineEdit(item.description)
        name.setReadOnly(True)
        self.procedure = QLineEdit(item.procedure_name)
        self.form.addRow("Display Text", name)
        self.form.addRow("Procedure Name", self.procedure)

        self.tabs = QTabWidget()
        self.tabs.setMinimumSize(350, 200)
        self._pages: list[_RunServerPage] = []
        for server in item.servers:
            page = _RunServerPage(server.host, server.databases)
            self._pages.append(page)
            self.tabs.addTab(page, server.tab_name)
        self.body.insertWidget(1, hline())
        self.body.insertWidget(2, self.tabs)

    def validate(self) -> None:
        if not self.procedure.text().strip():
            raise ValidationError("'Procedure Name' cannot be empty")
        if not self._pages:
            raise ValidationError("This item has no servers. Edit it to add one.")
        for server, page in zip(self._item.servers, self._pages):
            if not lines(page.databases.toPlainText()):
                raise ValidationError(f"Tab [{server.tab_name}] - the 'Databases' field is empty")

    def build_result(self) -> SQLCompareItem:
        servers = [dataclasses.replace(s, databases=lines(p.databases.toPlainText()))
                   for s, p in zip(self._item.servers, self._pages)]
        return dataclasses.replace(self._item, procedure_name=self.procedure.text().strip(),
                                   servers=servers)
