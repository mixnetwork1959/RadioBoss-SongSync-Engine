"""Windows subprocess helpers used by SongSync and its Setup Wizard."""

from __future__ import annotations

import os
import subprocess
from typing import Any


def hidden_window_options(
    *,
    os_name: str | None = None,
    subprocess_module: Any = subprocess,
) -> dict[str, Any]:
    """Return CreateProcess options which prevent a console window on Windows."""
    platform = os.name if os_name is None else os_name
    if platform != "nt":
        return {}

    startupinfo = subprocess_module.STARTUPINFO()
    startupinfo.dwFlags |= subprocess_module.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess_module.SW_HIDE
    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess_module.CREATE_NO_WINDOW,
    }


def run_without_window(
    command: list[str],
    *,
    os_name: str | None = None,
    subprocess_module: Any = subprocess,
    **kwargs: Any,
) -> Any:
    """Run a child process without creating a Windows console window."""
    return subprocess_module.run(
        command,
        **kwargs,
        **hidden_window_options(
            os_name=os_name,
            subprocess_module=subprocess_module,
        ),
    )
