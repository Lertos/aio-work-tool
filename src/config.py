"""App-wide constants (replaces model/Config.java)."""
from pathlib import Path

APP_NAME = "Work AIO Tool"
ORG_NAME = "lertos"

RESOURCES = Path(__file__).resolve().parent / "resources"
EDIT_ICON = RESOURCES / "edit.png"
DELETE_ICON = RESOURCES / "delete.png"

DEFAULT_WINDOW_SIZE = (400, 500)

SPACING = 10          # dialogs: form gaps, margins, button spacing
TAB_SPACING = 6       # main tabs: gap between list, hint and buttons
ICON_SIZE = 18        # edit/delete icons in list rows
BUTTON_PADDING = 4
ROW_BUTTON_SIZE = ICON_SIZE + BUTTON_PADDING * 2
ROW_MARGIN = 4

TEXT_DONE = "gray"    # finished to-dos; readable in light and dark themes
TEXT_ERROR = "red"    # To-Do hint while in delete mode

TOAST_FADE_MS = 250
TOAST_HOLD_MS = 1250
