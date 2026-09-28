import tempfile
import unittest
from pathlib import Path

from src.model.items import ScriptItem
from src.services.powershell import ScriptError, parameters, run_script, write_script

try:
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def launcher(self, code):
        def launch(verb, file, params, working_dir):
            self.calls.append((verb, file, params))
            return code
        return launch

    def test_script_file_deletes_itself_then_runs_the_commands(self):
        path = write_script("Write-Host 'héllo'\nGet-Date", self.folder)
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))  # BOM for Windows PowerShell 5.1
        lines = data.decode("utf-8-sig").splitlines()
        self.assertEqual(lines[0], "Remove-Item -LiteralPath $PSCommandPath -ErrorAction SilentlyContinue")
        self.assertEqual(lines[1:], ["Write-Host 'héllo'", "Get-Date"])

    def test_normal_run_opens_a_powershell_window(self):
        self.assertTrue(run_script(ScriptItem("x", "Get-Date"), self.launcher(42), self.folder))
        verb, file, params = self.calls[0]
        self.assertEqual((verb, file), ("open", "powershell.exe"))
        self.assertIn("-NoExit", params)
        script = next(self.folder.glob("*.ps1"))  # left for PowerShell, which deletes it
        self.assertEqual(params, parameters(script))

    def test_elevated_run_uses_runas(self):
        run_script(ScriptItem("x", "Get-Date", run_as_admin=True), self.launcher(42), self.folder)
        self.assertEqual(self.calls[0][0], "runas")

    def test_declined_uac_prompt_is_not_an_error_and_cleans_up(self):
        item = ScriptItem("x", "Get-Date", run_as_admin=True)
        self.assertFalse(run_script(item, self.launcher(5), self.folder))
        self.assertEqual(list(self.folder.glob("*.ps1")), [])

    def test_launch_failure_raises_and_cleans_up(self):
        with self.assertRaises(ScriptError):
            run_script(ScriptItem("x", "Get-Date"), self.launcher(2), self.folder)
        self.assertEqual(list(self.folder.glob("*.ps1")), [])


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_round_trips_commands_and_elevated_flag(self):
        from src.ui.dialogs.item_form_dialog import ValidationError
        from src.ui.dialogs.simple_dialogs import ScriptDialog
        dialog = ScriptDialog(None)
        dialog.name.setText("Build")
        with self.assertRaises(ValidationError):
            dialog.validate()  # commands are required
        dialog.text.setPlainText("git pull\nnpm run build\n")
        dialog.elevated.setChecked(True)
        dialog.validate()
        self.assertEqual(dialog.build_result(), ScriptItem("Build", "git pull\nnpm run build", True))
        dialog.deleteLater()
        again = ScriptDialog(None, ScriptItem("Build", "git pull", True))
        self.assertTrue(again.elevated.isChecked())
        again.deleteLater()


if __name__ == "__main__":
    unittest.main()
