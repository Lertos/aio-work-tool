"""Top-level window (replaces view-tab-pane.fxml + ControllerMain)."""
from __future__ import annotations

from functools import partial

from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QTabWidget

from ..config import APP_NAME, DEFAULT_WINDOW_SIZE
from ..model.storage import Storage
from .tabs.promoter_tab import PromoterTab
from .tabs.simple_tabs import CopyTab, FoldersTab, InfoTab
from .tabs.sql_compare_tab import SqlCompareTab
from .tabs.surround_tab import SurroundTab
from .tabs.todo_tab import TodoTab


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        stores = storage.load_all()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)
        pages = [
            TodoTab(stores["todo"]),
            FoldersTab(stores["folders"]),
            CopyTab(stores["copy"]),
            PromoterTab(stores["promote"]),
            InfoTab(stores["info"]),
            SqlCompareTab(stores["sql_compare"]),
            SurroundTab(stores["surround"]),
        ]
        for i, page in enumerate(pages):
            self.tabs.addTab(page, page.TITLE)
            self.tabs.setTabToolTip(i, f"Press {i + 1}")
            shortcut = QShortcut(QKeySequence(str(i + 1)), self)  # number keys switch tabs
            shortcut.activated.connect(partial(self.tabs.setCurrentIndex, i))

        # Window size/position and last tab are remembered between runs
        # (the Java version had this as a TODO).
        self._settings = QSettings()
        geometry = self._settings.value("window/geometry")
        if geometry is None or not self.restoreGeometry(geometry):
            self.resize(*DEFAULT_WINDOW_SIZE)
        self.tabs.setCurrentIndex(int(self._settings.value("window/tab", 0)))

    def closeEvent(self, event) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/tab", self.tabs.currentIndex())
        super().closeEvent(event)
