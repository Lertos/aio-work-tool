"""Add/edit a SQL compare item and its server tabs (was SQLComparePopup).

Improvements over Java:
* ``ServerForm`` keeps its fields as attributes instead of looking them up by
  grid child index, so changing the layout can't break saving.
* Server tabs can be removed (close button on each tab).
* 'Databases' is always required; before, it was only checked when
  Integrated Security was on.
* Port is a spin box, so it can't be non-numeric; "Default" means use the
  driver's default port.
"""
from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import (QCheckBox, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox,
                               QPushButton, QSpinBox, QTabWidget, QWidget)

from ...config import SPACING
from ...model.items import ServerConfig, SQLCompareItem
from ..widgets import hline, lines, text_box
from .item_form_dialog import ItemFormDialog, ValidationError


class ServerForm(QWidget):
    def __init__(self, server: ServerConfig | None = None):
        super().__init__()
        self._form = QFormLayout(self)
        self._form.setHorizontalSpacing(SPACING)
        self._form.setVerticalSpacing(SPACING)

        self.host = QLineEdit()
        self.port = QSpinBox()
        self.port.setRange(-1, 65535)
        self.port.setSpecialValueText("Default")
        self.port.setValue(-1)
        self.integrated = QCheckBox("Windows authentication")
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.databases = text_box(placeholder="Each line is a new database", rows=3)

        self._form.addRow("Host", self.host)
        self._form.addRow("Port", self.port)
        self._form.addRow("Integrated Security", self.integrated)
        self._form.addRow("Username", self.username)
        self._form.addRow("Password", self.password)
        self._form.addRow("Databases", self.databases)

        if server:
            self.host.setText(server.host)
            self.port.setValue(server.port)
            self.integrated.setChecked(server.integrated_security)
            self.username.setText(server.username)
            self.password.setText(server.password)
            self.databases.setPlainText("\n".join(server.databases))

        self.integrated.toggled.connect(self._show_credentials)
        self._show_credentials(self.integrated.isChecked())

    def _show_credentials(self, integrated: bool) -> None:
        self._form.setRowVisible(self.username, not integrated)
        self._form.setRowVisible(self.password, not integrated)

    def problem(self) -> str | None:
        if not self.host.text().strip():
            return "the 'Host' field is empty"
        if not self.integrated.isChecked():
            if not self.username.text().strip():
                return "the 'Username' field is empty"
            if not self.password.text():
                return "the 'Password' field is empty"
        if not lines(self.databases.toPlainText()):
            return "the 'Databases' field is empty"
        return None

    def to_config(self, tab_name: str) -> ServerConfig:
        integrated = self.integrated.isChecked()
        return ServerConfig(
            tab_name=tab_name,
            host=self.host.text().strip(),
            port=self.port.value(),
            username="" if integrated else self.username.text().strip(),
            password="" if integrated else self.password.text(),
            integrated_security=integrated,
            databases=lines(self.databases.toPlainText()),
        )


class SqlCompareDialog(ItemFormDialog):
    def __init__(self, parent, item: SQLCompareItem | None = None):
        super().__init__(parent, "Edit SQL Compare" if item else "Add SQL Compare",
                         "Update" if item else "Add")
        self._item = item
        self.name = QLineEdit(item.description if item else "")
        self.procedure = QLineEdit(item.procedure_name if item else "")
        self.form.addRow("Display Text", self.name)
        self.form.addRow("Procedure Name", self.procedure)

        self.new_tab_name = QLineEdit()
        self.new_tab_name.setPlaceholderText("Server tab name, e.g. PROD")
        add_server = QPushButton("Add Server Tab")
        add_server.setAutoDefault(False)
        add_server.clicked.connect(self._add_server_clicked)
        add_row = QHBoxLayout()
        add_row.addWidget(self.new_tab_name, 1)
        add_row.addWidget(add_server)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setMinimumSize(350, 300)

        self.body.insertWidget(1, hline())
        self.body.insertLayout(2, add_row)
        self.body.insertWidget(3, self.tabs)

        for server in item.servers if item else []:
            self._add_server(server.tab_name, server)

    # ------------------------------------------------------------------- tabs
    def _server_pages(self) -> list[tuple[str, ServerForm]]:
        return [(self.tabs.tabText(i), self.tabs.widget(i)) for i in range(self.tabs.count())]

    def _add_server_clicked(self) -> None:
        name = self.new_tab_name.text().strip()
        if not name:
            QMessageBox.warning(self, self.windowTitle(), "'Tab Name' must not be empty")
            return
        if any(name.lower() == existing.lower() for existing, _ in self._server_pages()):
            QMessageBox.warning(self, self.windowTitle(), "'Tab Name' must be unique")
            return
        self._add_server(name)
        self.new_tab_name.clear()

    def _add_server(self, name: str, server: ServerConfig | None = None) -> None:
        page = ServerForm(server)
        self.tabs.addTab(page, name)
        self.tabs.setCurrentWidget(page)

    def _close_tab(self, index: int) -> None:
        answer = QMessageBox.question(self, self.windowTitle(),
                                      f"Remove server tab '{self.tabs.tabText(index)}'?")
        if answer == QMessageBox.StandardButton.Yes:
            page = self.tabs.widget(index)
            self.tabs.removeTab(index)
            page.deleteLater()

    # ------------------------------------------------------------- validation
    def validate(self) -> None:
        if not self.name.text().strip():
            raise ValidationError("'Display Text' cannot be empty")
        if not self.procedure.text().strip():
            raise ValidationError("'Procedure Name' cannot be empty")
        pages = self._server_pages()
        if not pages:
            raise ValidationError("Add at least one server tab")
        for tab_name, page in pages:
            problem = page.problem()
            if problem:
                self.tabs.setCurrentWidget(page)
                raise ValidationError(f"Tab [{tab_name}] - {problem}")

    def build_result(self) -> SQLCompareItem:
        fields = dict(
            description=self.name.text().strip(),
            procedure_name=self.procedure.text().strip(),
            servers=[page.to_config(name) for name, page in self._server_pages()],
        )
        if self._item:  # keep the same id so saved passwords stay linked
            return dataclasses.replace(self._item, **fields)
        return SQLCompareItem(**fields)
