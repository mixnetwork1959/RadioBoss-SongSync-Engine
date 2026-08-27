from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sftp_host_keys import (
    resolve_known_hosts_file,
    save_server_host_key,
    select_known_hosts,
)


class FakeServerKey:
    def export_public_key(self, _format):
        return b"ssh-ed25519 AAAATEST server"


class FakeConnection:
    def get_server_host_key(self):
        return FakeServerKey()


class SftpHostKeyTests(unittest.TestCase):
    def test_default_file_is_always_next_to_application(self):
        app_dir = Path(r"D:\RadioBOSS Toolkit\tools\SongSync")
        self.assertEqual(
            resolve_known_hosts_file(app_dir),
            app_dir / "sftp_known_hosts",
        )

    def test_missing_file_is_rejected_when_tofu_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                select_known_hosts(Path(directory), "", False)

    def test_missing_file_uses_tofu_and_is_created_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, known_hosts, trust_first = select_known_hosts(root, "", True)

            self.assertIsNone(known_hosts)
            self.assertTrue(trust_first)
            save_server_host_key(FakeConnection(), "example.org", 22, path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "example.org ssh-ed25519 AAAATEST server\n",
            )
            self.assertFalse(path.with_name("sftp_known_hosts.tmp").exists())

    def test_nonstandard_port_uses_bracketed_host_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sftp_known_hosts"
            save_server_host_key(FakeConnection(), "example.org", 2222, path)
            self.assertTrue(path.read_text().startswith("[example.org]:2222 "))


if __name__ == "__main__":
    unittest.main()
