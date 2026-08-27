from __future__ import annotations

import tkinter as tk


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    root.destroy()
    print("TKINTER_BUNDLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
