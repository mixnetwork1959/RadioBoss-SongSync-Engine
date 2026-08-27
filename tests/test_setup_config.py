from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from setup_wizard import build_config, test_sftp


def sample_values() -> dict:
    return {
        "db_type": "sqlite",
        "sqlite_mode": "dedicated",
        "sqlite_database": "auto",
        "db_host": "127.0.0.1",
        "db_port": "3306",
        "db_name": "radioboss",
        "db_user": "readonly",
        "db_password": "secret",
        "db_charset": "utf8mb4",
        "public_export_dir": "exports/public",
        "private_export_dir": "exports/private",
        "scheduler_export_enabled": False,
        "scheduler_sdl_file": "",
        "show_examples": True,
        "example_limit": "10",
        "sftp_enabled": True,
        "sftp_host": "example.org",
        "sftp_port": "22",
        "sftp_username": "radio",
        "sftp_password": "",
        "sftp_private_key_file": "sftp_key",
        "sftp_private_key_passphrase": "",
        "sftp_remote_public_dir": "/public",
        "sftp_remote_private_dir": "/private",
        "sftp_timeout": "20",
        "sftp_trust_on_first_use": True,
        "sftp_known_hosts_file": "sftp_known_hosts",
    }


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *_args):
        return False


class FakeSftp:
    async def isdir(self, _path):
        return True


class FakeServerKey:
    def export_public_key(self, _format):
        return b"ssh-ed25519 AAAATEST server"


class FakeConnection:
    def get_server_host_key(self):
        return FakeServerKey()

    def start_sftp_client(self):
        return AsyncContext(FakeSftp())


class SetupConfigTests(unittest.TestCase):
    def test_build_config_creates_typed_json_values(self):
        config = build_config(sample_values())

        self.assertIs(config["SFTP_ENABLED"], True)
        self.assertEqual(config["SFTP_PORT"], 22)
        self.assertEqual(config["EXAMPLE_LIMIT"], 10)
        self.assertEqual(config["SFTP_KNOWN_HOSTS_FILE"], "sftp_known_hosts")

    def test_setup_test_creates_known_hosts_without_windows_openssh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sftp_key").write_text("private key", encoding="utf-8")
            fake_asyncssh = types.SimpleNamespace(
                read_private_key=lambda *_args, **_kwargs: object(),
                connect=lambda *_args, **_kwargs: AsyncContext(FakeConnection()),
            )

            with patch.dict(sys.modules, {"asyncssh": fake_asyncssh}):
                ok, message = test_sftp(sample_values(), root)

            self.assertTrue(ok, message)
            self.assertIn("server key was saved", message)
            self.assertTrue((root / "sftp_known_hosts").is_file())


if __name__ == "__main__":
    unittest.main()
