from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from windows_process import hidden_window_options, run_without_window


class FakeStartupInfo:
    def __init__(self) -> None:
        self.dwFlags = 0
        self.wShowWindow = None


class FakeSubprocess:
    STARTUPINFO = FakeStartupInfo
    STARTF_USESHOWWINDOW = 0x01
    SW_HIDE = 0
    CREATE_NO_WINDOW = 0x08000000
    last_run = None

    @classmethod
    def run(cls, command, **kwargs):
        cls.last_run = (command, kwargs)
        return "completed"


class HiddenWindowOptionsTests(unittest.TestCase):
    def test_non_windows_returns_no_process_options(self):
        self.assertEqual(hidden_window_options(os_name="posix"), {})

    def test_windows_hides_child_console(self):
        options = hidden_window_options(
            os_name="nt",
            subprocess_module=FakeSubprocess,
        )

        startupinfo = options["startupinfo"]
        self.assertEqual(
            startupinfo.dwFlags & FakeSubprocess.STARTF_USESHOWWINDOW,
            FakeSubprocess.STARTF_USESHOWWINDOW,
        )
        self.assertEqual(startupinfo.wShowWindow, FakeSubprocess.SW_HIDE)
        self.assertEqual(
            options["creationflags"],
            FakeSubprocess.CREATE_NO_WINDOW,
        )

    def test_runner_forwards_hidden_window_options(self):
        result = run_without_window(
            ["sftp.exe", "server"],
            os_name="nt",
            subprocess_module=FakeSubprocess,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result, "completed")
        command, options = FakeSubprocess.last_run
        self.assertEqual(command, ["sftp.exe", "server"])
        self.assertTrue(options["text"])
        self.assertTrue(options["capture_output"])
        self.assertEqual(
            options["creationflags"],
            FakeSubprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(
            options["startupinfo"].wShowWindow,
            FakeSubprocess.SW_HIDE,
        )


if __name__ == "__main__":
    unittest.main()
