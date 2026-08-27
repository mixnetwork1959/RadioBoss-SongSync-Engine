from __future__ import annotations

from pathlib import Path


DEFAULT_KNOWN_HOSTS_FILE = "sftp_known_hosts"


def resolve_known_hosts_file(app_dir: Path, configured: str = "") -> Path:
    value = str(configured or DEFAULT_KNOWN_HOSTS_FILE).strip()
    path = Path(value).expanduser()
    return path if path.is_absolute() else app_dir / path


def select_known_hosts(
    app_dir: Path,
    configured: str,
    trust_on_first_use: bool,
) -> tuple[Path, str | None, bool]:
    path = resolve_known_hosts_file(app_dir, configured)

    if path.is_file():
        return path, str(path), False

    if trust_on_first_use:
        return path, None, True

    raise RuntimeError(
        "SFTP host key is unknown and trust-on-first-use is disabled."
    )


def known_host_name(host: str, port: int) -> str:
    return host if port == 22 else f"[{host}]:{port}"


def save_server_host_key(
    connection,
    host: str,
    port: int,
    known_hosts_file: Path,
) -> None:
    server_key = connection.get_server_host_key()
    exported_key = server_key.export_public_key("openssh")

    if isinstance(exported_key, bytes):
        exported_key = exported_key.decode("ascii")

    known_hosts_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = known_hosts_file.with_name(known_hosts_file.name + ".tmp")
    temporary_path.write_text(
        f"{known_host_name(host, port)} {exported_key.strip()}\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary_path.replace(known_hosts_file)
