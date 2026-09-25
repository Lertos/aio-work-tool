"""Entry point: ``python -m src`` from the project folder."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import APP_NAME, ORG_NAME
from .model.storage import KeyringSecrets, MemorySecrets, Storage
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)

    # Windows: C:\Users\<you>\AppData\Roaming\lertos\Work AIO Tool
    data_dir = Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation))
    try:
        secrets = KeyringSecrets()
    except ImportError:
        secrets = MemorySecrets()

    window = MainWindow(Storage(data_dir, secrets))
    window.show()

    if isinstance(secrets, MemorySecrets):
        QMessageBox.warning(window, APP_NAME,
                            "The 'keyring' package isn't installed, so SQL passwords and connection strings will "
                            "only be kept until the app closes.\n\nInstall it with:\n"
                            "    pip install keyring")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
