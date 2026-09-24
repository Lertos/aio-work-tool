"""Base for every add/edit/run popup (replaces the static *Popup.display() methods).

Fixes Java bug #1. The Java popups kept their result in static fields that
were never cleared, so pressing Cancel returned whatever the previous call
produced - and the Promoter tab would re-run the last promotion. Here each
call builds a fresh dialog and ``build_result()`` is only called after the
user presses the accept button, so Cancel always yields ``None``.

Usage from a tab::

    item = PromoteDialog.ask(self, existing, mode=Mode.RUN)
    if item is not None:
        promote(item)
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QMessageBox,
                               QVBoxLayout, QWidget)

from ...config import SPACING


class ValidationError(Exception):
    """Raise from validate() with a user-facing message; the dialog stays open."""


class ItemFormDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, accept_text: str = "Save"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._result: Any = None

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setHorizontalSpacing(SPACING)
        self.form.setVerticalSpacing(SPACING)

        self.buttons = QDialogButtonBox()
        self.cancel_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.accept_button = self.buttons.addButton(accept_text,
                                                    QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.setCenterButtons(True)
        self.buttons.accepted.connect(self._try_accept)
        self.buttons.rejected.connect(self.reject)

        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        self.body.setSpacing(SPACING)
        self.body.addLayout(self.form)
        # Subclasses add extra widgets before the buttons with self.body.insertWidget(index, w)
        self.body.addWidget(self.buttons)

    # ------------------------------------------------------------ override these
    def validate(self) -> None:
        """Raise ValidationError(message) if the form is not acceptable."""

    def build_result(self) -> Any:
        raise NotImplementedError

    # ------------------------------------------------------------------- public
    @classmethod
    def ask(cls, parent: QWidget | None, *args, **kwargs) -> Any | None:
        """Show a fresh dialog; return the result, or None if cancelled."""
        dialog = cls(parent, *args, **kwargs)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                return dialog._result
            return None
        finally:
            dialog.deleteLater()

    # ------------------------------------------------------------------ private
    def _try_accept(self) -> None:
        try:
            self.validate()
            self._result = self.build_result()
        except ValidationError as err:
            QMessageBox.warning(self, self.windowTitle(), str(err))
            return
        self.accept()
