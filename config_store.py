from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when a private SongSync configuration cannot be loaded."""


def read_json_config(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read {path.name}: {exc}") from exc

    if not isinstance(value, dict):
        raise ConfigError(f"{path.name} must contain one JSON object.")

    return value


def read_legacy_python_config(path: Path) -> dict:
    try:
        values = runpy.run_path(str(path))
    except Exception as exc:
        raise ConfigError(f"Could not import {path.name}: {exc}") from exc

    return {
        name: value
        for name, value in values.items()
        if not name.startswith("__")
    }


def load_existing_config(json_path: Path, legacy_path: Path) -> dict:
    if json_path.is_file():
        return read_json_config(json_path)

    if legacy_path.is_file():
        return read_legacy_python_config(legacy_path)

    return {}


def write_json_config(path: Path, values: dict) -> Path | None:
    if not isinstance(values, dict):
        raise TypeError("SongSync configuration must be a dictionary.")

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")
    backup_path = path.with_name(path.name + ".bak")
    created_backup: Path | None = None

    if path.is_file():
        backup_temporary = backup_path.with_name(backup_path.name + ".tmp")
        shutil.copy2(path, backup_temporary)
        backup_temporary.replace(backup_path)
        created_backup = backup_path

    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(values, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary_path.replace(path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

    return created_backup
