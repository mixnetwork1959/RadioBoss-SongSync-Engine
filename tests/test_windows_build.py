from __future__ import annotations

import unittest
from pathlib import Path


class WindowsBuildScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.script = (cls.root / "build_windows.bat").read_text(
            encoding="utf-8"
        )
        cls.smoke_test = (cls.root / "tkinter_bundle_smoke_test.py").read_text(
            encoding="utf-8"
        )

    def test_current_pyinstaller_release_is_pinned(self):
        self.assertIn("pyinstaller==6.22.2", self.script.casefold())

    def test_tkinter_onefile_smoke_test_is_built_and_run(self):
        self.assertIn("tkinter_bundle_smoke_test.py", self.script)
        self.assertIn("--name SongSync-Tk-Smoke-Test", self.script)
        self.assertIn('"dist\\SongSync-Tk-Smoke-Test.exe"', self.script)
        self.assertIn("goto :tk_bundle_error", self.script)

    def test_smoke_test_opens_a_real_tk_root(self):
        self.assertIn("root = tk.Tk()", self.smoke_test)
        self.assertIn("TKINTER_BUNDLE_OK", self.smoke_test)

    def test_embedded_tcl_tk_is_left_to_pyinstaller(self):
        script = self.script.casefold()
        self.assertNotIn("tcl_data_dir", script)
        self.assertNotIn("tk_data_dir", script)
        self.assertNotIn("--add-data", script)
        self.assertNotIn("pyi-archive_viewer", script)
        self.assertNotIn("write_tk_build_paths.py", script)
        self.assertNotIn("for /f", script)

    def test_all_three_expected_executables_are_verified(self):
        for filename in (
            "RadioBOSS-SongSync.exe",
            "RadioBOSS-SongSync-Setup.exe",
            "RadioBOSS-SongSync-Debug.exe",
        ):
            self.assertIn(f'if not exist "dist\\{filename}"', self.script)

    def test_success_message_requires_smoke_test_and_all_outputs(self):
        smoke_run = self.script.index('"dist\\SongSync-Tk-Smoke-Test.exe"')
        output_check = self.script.index(
            'if not exist "dist\\RadioBOSS-SongSync.exe"'
        )
        success = self.script.index(
            "Build completed and Tkinter onefile test passed"
        )
        self.assertLess(smoke_run, output_check)
        self.assertLess(output_check, success)


if __name__ == "__main__":
    unittest.main()
