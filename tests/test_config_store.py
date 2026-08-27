from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config_store import ConfigError, load_existing_config, write_json_config


class ConfigStoreTests(unittest.TestCase):
    def test_existing_json_is_replaced_and_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            original = {"SFTP_ENABLED": False, "marker": "old"}
            path.write_text(json.dumps(original), encoding="utf-8")

            backup = write_json_config(
                path,
                {"SFTP_ENABLED": True, "marker": "new"},
            )

            self.assertEqual(json.loads(path.read_text()), {
                "SFTP_ENABLED": True,
                "marker": "new",
            })
            self.assertEqual(json.loads(backup.read_text()), original)

    def test_first_write_does_not_create_fake_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            backup = write_json_config(path, {"DB_TYPE": "sqlite"})

            self.assertIsNone(backup)
            self.assertFalse((Path(directory) / "config.json.bak").exists())

    def test_invalid_json_is_reported_instead_of_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text("{broken", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_existing_config(root / "config.json", root / "config.py")

    def test_legacy_python_config_is_loaded_only_without_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "config.py"
            legacy.write_text("DB_TYPE = 'sqlite'\nEXAMPLE_LIMIT = 7\n")

            values = load_existing_config(root / "config.json", legacy)
            self.assertEqual(values["DB_TYPE"], "sqlite")
            self.assertEqual(values["EXAMPLE_LIMIT"], 7)

            write_json_config(root / "config.json", {"DB_TYPE": "mysql"})
            values = load_existing_config(root / "config.json", legacy)
            self.assertEqual(values, {"DB_TYPE": "mysql"})


if __name__ == "__main__":
    unittest.main()
