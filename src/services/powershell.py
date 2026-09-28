"""Run a saved list of PowerShell commands in its own console window (Scripts tab). Windows only.

* The commands are written to a temporary .ps1 file, which deletes itself as
  soon as PowerShell starts it (PowerShell has read the whole file by then).
* Windows PowerShell runs it in a new window that stays open afterwards, so the
  output and any errors can be read.
* "Needs Elevated Access" launches through ShellExecute's "runas" verb, which
  shows the UAC prompt. Saying No there just means nothing runs.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Callable

from ..model.items import ScriptItem

POWERSHELL = "powershell.exe"
_SELF_DELETE = "Remove-Item -LiteralPath $PSCommandPath -ErrorAction SilentlyContinue\n"
_SE_ERR_ACCESSDENIED = 5  # ShellExecute's answer when the UAC prompt is declined

# launch(verb, file, parameters, working_dir) -> ShellExecute result (> 32 means started)
Launcher = Callable[[str, str, str, str], int]


class ScriptError(Exception):
    """PowerShell could not be started; the message is shown to the user."""


def write_script(commands: str, folder: Path | None = None) -> Path:
    # UTF-8 with a BOM, so Windows PowerShell 5.1 reads non-ASCII characters correctly.
    fd, path = tempfile.mkstemp(prefix="work-aio-", suffix=".ps1", dir=folder)
    with os.fdopen(fd, "w", encoding="utf-8-sig") as fh:
        fh.write(_SELF_DELETE + commands + "\n")
    return Path(path)


def parameters(script: Path) -> str:
    return f'-NoProfile -ExecutionPolicy Bypass -NoExit -File "{script}"'


def run_script(item: ScriptItem, launch: Launcher | None = None,
               folder: Path | None = None) -> bool:
    """Start the script. Returns False if the UAC prompt was declined."""
    if launch is None:
        if sys.platform != "win32":
            raise ScriptError("Scripts can only be run on Windows")
        launch = _shell_execute
    script = write_script(item.commands, folder)
    verb = "runas" if item.run_as_admin else "open"
    code = launch(verb, POWERSHELL, parameters(script), str(Path.home()))
    if code > 32:
        return True
    script.unlink(missing_ok=True)  # PowerShell never started, so it can't delete it
    if item.run_as_admin and code == _SE_ERR_ACCESSDENIED:
        return False
    raise ScriptError(f"PowerShell could not be started (error {code})")


def _shell_execute(verb: str, file: str, params: str, working_dir: str) -> int:
    import ctypes
    from ctypes import wintypes

    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                              wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]
    shell_execute.restype = ctypes.c_void_p
    return shell_execute(None, verb, file, params, working_dir, 1) or 0  # 1 = SW_SHOWNORMAL
