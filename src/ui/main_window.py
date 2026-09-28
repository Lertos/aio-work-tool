"""Top-level window (replaces view-tab-pane.fxml + ControllerMain)."""
from __future__ import annotations

from functools import partial

from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QTabWidget

from ..config import APP_NAME, DEFAULT_WINDOW_SIZE
from ..model.storage import Storage
from .tabs.promoter_tab import PromoterTab
from .tabs.saved_query_tab import SavedQueryTab
from .tabs.schema_backup_tab import SchemaBackupTab
from .tabs.simple_tabs import CopyTab, FoldersTab, InfoTab, ScriptsTab
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
            SchemaBackupTab(stores["schema_backup"]),
            SavedQueryTab(stores["queries"]),
            ScriptsTab(stores["scripts"]),
        ]
        for i, page in enumerate(pages):
            self.tabs.addTab(page, page.TITLE)
            if i < 10:  # number keys switch tabs: 1-9, then 0 for the tenth
                key = str((i + 1) % 10)
                self.tabs.setTabToolTip(i, f"Press {key}")
                shortcut = QShortcut(QKeySequence(key), self)
                shortcut.activated.connect(partial(self.tabs.setCurrentIndex, i))

        # Window size/position and last tab are remembered between runs
        # (the Java version had this as a TODO).
        self._settings = QSettings()
        geometry = self._settings.value("window/geometry")
        if geometry is None or not self.restoreGeometry(geometry):
            # First run: wide enough to show every tab label without the scroll arrows.
            width, height = DEFAULT_WINDOW_SIZE
            self.resize(max(width, self.tabs.tabBar().sizeHint().width()), height)
        self.tabs.setCurrentIndex(int(self._settings.value("window/tab", 0)))

    def closeEvent(self, event) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/tab", self.tabs.currentIndex())
        super().closeEvent(event)
