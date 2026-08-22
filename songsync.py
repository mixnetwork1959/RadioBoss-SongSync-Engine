# ==========================================================
# RadioBOSS SongSync Engine
# Version 1.7.2
# songsync.py
# ==========================================================

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import posixpath
import runpy
import shutil
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

from scheduler_export import create_scheduler_payload
from windows_process import run_without_window

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None

    class MySQLError(Exception):
        pass

try:
    import asyncssh
except ImportError:
    print("ERROR: asyncssh is not installed.")
    print("Install it with:")
    print("    py -m pip install -r requirements.txt")
    raise SystemExit(1)


VERSION = "1.7.2"


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = application_dir()


def resolve_local_path(value: str) -> Path:
    path = Path(value).expanduser()

    if path.is_absolute():
        return path

    return APP_DIR / path


def load_config():
    config_path = APP_DIR / "config.py"
    open_setup = "--setup" in sys.argv

    if open_setup or not config_path.is_file():
        try:
            from setup_wizard import run_setup
        except Exception as exc:
            if not config_path.is_file():
                print("ERROR: Setup Wizard could not be loaded.")
                print(f"{type(exc).__name__}: {exc}")
                raise SystemExit(1) from exc
        else:
            if not run_setup(APP_DIR):
                raise SystemExit(0)

    if not config_path.is_file():
        raise SystemExit(1)

    try:
        config = runpy.run_path(str(config_path))
    except Exception as exc:
        print("ERROR while loading config.py:")
        print(f"{type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc

    required = [
        "PUBLIC_EXPORT_DIR",
        "PRIVATE_EXPORT_DIR",
        "SHOW_EXAMPLES",
        "EXAMPLE_LIMIT",
        "SFTP_ENABLED",
    ]

    missing = [name for name in required if name not in config]

    if missing:
        print("ERROR: Missing setting(s) in config.py:")
        for name in missing:
            print(f"  - {name}")
        raise SystemExit(1)

    public_settings = {
        name: value
        for name, value in config.items()
        if not name.startswith("__")
    }

    settings = SimpleNamespace(**public_settings)
    settings.DB_TYPE = str(
        getattr(settings, "DB_TYPE", "mysql")
    ).strip().lower()

    if settings.DB_TYPE == "mysql":
        mysql_required = [
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "DB_CHARSET",
        ]
        mysql_missing = [
            name for name in mysql_required
            if not hasattr(settings, name)
        ]

        if mysql_missing:
            print("ERROR: Missing MySQL setting(s) in config.py:")
            for name in mysql_missing:
                print(f"  - {name}")
            raise SystemExit(1)

    elif settings.DB_TYPE == "sqlite":
        settings.SQLITE_MODE = str(
            getattr(settings, "SQLITE_MODE", "dedicated")
        ).strip().lower()
        settings.SQLITE_DATABASE = str(
            getattr(settings, "SQLITE_DATABASE", "auto")
        ).strip()

        if settings.SQLITE_MODE not in {"shared", "dedicated"}:
            print("ERROR: SQLITE_MODE must be 'shared' or 'dedicated'.")
            raise SystemExit(1)

    else:
        print("ERROR: DB_TYPE must be 'mysql' or 'sqlite'.")
        raise SystemExit(1)

    return settings


CONFIG = load_config()

PUBLIC_DIR = resolve_local_path(CONFIG.PUBLIC_EXPORT_DIR)
PRIVATE_DIR = resolve_local_path(CONFIG.PRIVATE_EXPORT_DIR)

SONGS_FILE = PUBLIC_DIR / "songs.json"
ARTISTS_FILE = PUBLIC_DIR / "artists.json"
GENRES_FILE = PUBLIC_DIR / "genres.json"
INFO_FILE = PUBLIC_DIR / "info.json"

LOOKUP_FILE = PRIVATE_DIR / "lookup.json"
DUPLICATE_LOG_FILE = PRIVATE_DIR / "duplicates.log"
SCHEDULER_EVENTS_FILE = PRIVATE_DIR / "scheduler-events.json"


@dataclass(frozen=True)
class Song:
    track_id: int
    artist: str
    title: str
    filename: str
    genre: str
    playcount: int
    lastplayed: str
    play_history: tuple[str, ...]
    valid: int | None
    disabled: int | None

    @property
    def duplicate_key(self) -> tuple[str, str]:
        return (
            normalize_text(self.artist),
            normalize_text(self.title),
        )



def normalize_datetime_value(value) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")

    return str(value).strip()


def parse_play_history(value) -> tuple[str, ...]:
    if value is None:
        return ()

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return tuple(line.strip() for line in text.split("\n") if line.strip())


def normalize_text(value: str) -> str:
    return " ".join((value or "").casefold().split())


def find_sqlite_database() -> Path:
    configured = CONFIG.SQLITE_DATABASE

    if configured.casefold() != "auto":
        database_path = resolve_local_path(configured)

        if not database_path.is_file():
            raise FileNotFoundError(
                f"SQLite database was not found: {database_path}"
            )

        return database_path

    appdata = os.environ.get("APPDATA", "").strip()

    if not appdata:
        raise RuntimeError(
            "Windows APPDATA could not be determined."
        )

    radio_root = Path(appdata) / "djsoft.net"

    if CONFIG.SQLITE_MODE == "shared":
        database_path = radio_root / "tracks.db"

        if not database_path.is_file():
            raise FileNotFoundError(
                f"Shared RadioBOSS database was not found: {database_path}"
            )

        return database_path

    matches = sorted(
        path
        for path in radio_root.glob("RadioBOSS_*/tracks.db")
        if path.is_file()
    )

    if not matches:
        raise FileNotFoundError(
            "No dedicated RadioBOSS tracks.db was found below: "
            f"{radio_root}"
        )

    if len(matches) > 1:
        options = "\n".join(f"  - {path}" for path in matches)
        raise RuntimeError(
            "Multiple dedicated RadioBOSS databases were found.\n"
            "Enter the required path as SQLITE_DATABASE in config.py:\n"
            f"{options}"
        )

    return matches[0]


def database_label() -> str:
    if CONFIG.DB_TYPE == "sqlite":
        return str(find_sqlite_database())

    return str(CONFIG.DB_NAME)


def connect_database():
    if CONFIG.DB_TYPE == "sqlite":
        database_path = find_sqlite_database()
        connection = sqlite3.connect(
            f"file:{database_path.as_posix()}?mode=ro",
            uri=True,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    if mysql is None:
        raise RuntimeError(
            "mysql-connector-python is required for DB_TYPE = 'mysql'."
        )

    return mysql.connector.connect(
        host=CONFIG.DB_HOST,
        port=CONFIG.DB_PORT,
        database=CONFIG.DB_NAME,
        user=CONFIG.DB_USER,
        password=CONFIG.DB_PASSWORD,
        charset=CONFIG.DB_CHARSET,
        use_unicode=True,
        use_pure=True,
        autocommit=True,
        connection_timeout=10,
    )


def verify_required_tables(connection) -> None:
    required = {"tracks2", "taginfo"}

    cursor = connection.cursor()

    if CONFIG.DB_TYPE == "sqlite":
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name IN ('tracks2', 'taginfo')
            """
        )
    else:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name IN ('tracks2', 'taginfo')
            """,
            (CONFIG.DB_NAME,),
        )

    found = {row[0] for row in cursor.fetchall()}
    cursor.close()

    missing = required - found

    if missing:
        raise RuntimeError(
            "Required RadioBOSS table(s) missing: " + ", ".join(sorted(missing))
        )


def load_songs(connection) -> list[Song]:
    sql = """
        SELECT
            t.track_id,
            t.fn AS filename,
            t.valid,
            t.disablesong,
            COALESCE(t.playcount, 0) AS playcount,
            t.lastplayed,
            t.lastplayedhistory,
            COALESCE(i.artist, '') AS artist,
            COALESCE(i.title, '') AS title,
            COALESCE(i.genre, '') AS genre
        FROM tracks2 AS t
        LEFT JOIN taginfo AS i
            ON i.track_id = t.track_id
        ORDER BY t.track_id
    """

    if CONFIG.DB_TYPE == "sqlite":
        cursor = connection.cursor()
    else:
        cursor = connection.cursor(dictionary=True)
    cursor.execute(sql)

    songs: list[Song] = []

    for row in cursor:
        songs.append(
            Song(
                track_id=int(row["track_id"]),
                artist=(row["artist"] or "").strip(),
                title=(row["title"] or "").strip(),
                filename=(row["filename"] or "").strip(),
                genre=(row["genre"] or "").strip(),
                playcount=max(0, int(row["playcount"] or 0)),
                lastplayed=normalize_datetime_value(row["lastplayed"]),
                play_history=parse_play_history(row["lastplayedhistory"]),
                valid=row["valid"],
                disabled=row["disablesong"],
            )
        )

    cursor.close()
    return songs


def is_usable(song: Song) -> bool:
    if not song.filename:
        return False

    if not song.artist or not song.title:
        return False

    if song.valid is not None and int(song.valid) == 0:
        return False

    if song.disabled is not None and int(song.disabled) != 0:
        return False

    return True


def create_unique_catalog(
    songs: Iterable[Song],
) -> tuple[list[Song], dict[tuple[str, str], list[Song]]]:
    unique: dict[tuple[str, str], Song] = {}
    groups: dict[tuple[str, str], list[Song]] = defaultdict(list)

    for song in songs:
        key = song.duplicate_key
        groups[key].append(song)

        if key not in unique:
            unique[key] = song

    duplicate_groups = {
        key: entries
        for key, entries in groups.items()
        if len(entries) > 1
    }

    return list(unique.values()), duplicate_groups


def atomic_json_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    temp_path.replace(path)


def validate_sftp_config() -> None:
    if not CONFIG.SFTP_ENABLED:
        return

    required = [
        "SFTP_HOST",
        "SFTP_PORT",
        "SFTP_USERNAME",
        "SFTP_PASSWORD",
        "SFTP_PRIVATE_KEY_FILE",
        "SFTP_PRIVATE_KEY_PASSPHRASE",
        "SFTP_REMOTE_PUBLIC_DIR",
        "SFTP_REMOTE_PRIVATE_DIR",
        "SFTP_TIMEOUT",
        "SFTP_TRUST_ON_FIRST_USE",
        "SFTP_KNOWN_HOSTS_FILE",
    ]

    missing = [name for name in required if not hasattr(CONFIG, name)]

    if missing:
        raise RuntimeError(
            "Missing SFTP setting(s): " + ", ".join(missing)
        )

    text_settings = [
        "SFTP_HOST",
        "SFTP_USERNAME",
        "SFTP_REMOTE_PUBLIC_DIR",
        "SFTP_REMOTE_PRIVATE_DIR",
        "SFTP_KNOWN_HOSTS_FILE",
    ]

    empty = [
        name
        for name in text_settings
        if not str(getattr(CONFIG, name, "")).strip()
    ]

    if empty:
        raise RuntimeError(
            "Empty SFTP setting(s): " + ", ".join(empty)
        )

    if int(CONFIG.SFTP_PORT) < 1 or int(CONFIG.SFTP_PORT) > 65535:
        raise RuntimeError("SFTP_PORT must be between 1 and 65535.")

    if int(CONFIG.SFTP_TIMEOUT) < 1:
        raise RuntimeError("SFTP_TIMEOUT must be at least 1 second.")

    password = str(CONFIG.SFTP_PASSWORD).strip()
    private_key_file = str(CONFIG.SFTP_PRIVATE_KEY_FILE).strip()

    if not password and not private_key_file:
        raise RuntimeError(
            "Enter SFTP_PASSWORD or SFTP_PRIVATE_KEY_FILE."
        )

    if (
        private_key_file
        and not resolve_local_path(private_key_file).is_file()
    ):
        raise RuntimeError(
            f"SFTP private key file was not found: {private_key_file}"
        )


def remote_join(directory: str, filename: str) -> str:
    directory = str(directory).replace("\\", "/").rstrip("/")
    return posixpath.join(directory, filename)


def configured_sftp_uploads() -> list[tuple[Path, str]]:
    public_dir = str(CONFIG.SFTP_REMOTE_PUBLIC_DIR)
    private_dir = str(CONFIG.SFTP_REMOTE_PRIVATE_DIR)
    uploads = [
        (SONGS_FILE, remote_join(public_dir, SONGS_FILE.name)),
        (ARTISTS_FILE, remote_join(public_dir, ARTISTS_FILE.name)),
        (GENRES_FILE, remote_join(public_dir, GENRES_FILE.name)),
        (INFO_FILE, remote_join(public_dir, INFO_FILE.name)),
        (LOOKUP_FILE, remote_join(private_dir, LOOKUP_FILE.name)),
    ]

    if bool(getattr(CONFIG, "SCHEDULER_EXPORT_ENABLED", False)):
        uploads.append(
            (
                SCHEDULER_EVENTS_FILE,
                remote_join(private_dir, SCHEDULER_EVENTS_FILE.name),
            )
        )

    return uploads


def known_host_name(host: str, port: int) -> str:
    return host if port == 22 else f"[{host}]:{port}"


def save_asyncssh_host_key(
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
    known_hosts_file.write_text(
        f"{known_host_name(host, port)} {exported_key.strip()}\n",
        encoding="utf-8",
        newline="\n",
    )


async def replace_remote_file(
    sftp,
    local_path: Path,
    remote_path: str,
) -> None:
    temporary_path = remote_path + ".tmp"

    try:
        await sftp.remove(temporary_path)
    except (OSError, asyncssh.SFTPError):
        pass

    await sftp.put(str(local_path), temporary_path)

    try:
        await sftp.posix_rename(temporary_path, remote_path)
        return
    except (OSError, asyncssh.SFTPError):
        pass

    try:
        await sftp.remove(remote_path)
    except (OSError, asyncssh.SFTPError):
        pass

    await sftp.rename(temporary_path, remote_path)


async def upload_exports_async() -> None:
    validate_sftp_config()

    host = str(CONFIG.SFTP_HOST).strip()
    port = int(CONFIG.SFTP_PORT)
    username = str(CONFIG.SFTP_USERNAME).strip()
    password = str(CONFIG.SFTP_PASSWORD).strip()
    timeout = int(CONFIG.SFTP_TIMEOUT)
    known_hosts_file = resolve_local_path(CONFIG.SFTP_KNOWN_HOSTS_FILE)
    private_key_file = str(CONFIG.SFTP_PRIVATE_KEY_FILE).strip()
    private_key_passphrase = str(CONFIG.SFTP_PRIVATE_KEY_PASSPHRASE)

    if private_key_file:
        private_key_path = resolve_local_path(private_key_file)
        client_keys = [
            asyncssh.read_private_key(
                str(private_key_path),
                passphrase=private_key_passphrase or None,
            )
        ]
        password = None
        preferred_auth = "publickey"
    else:
        client_keys = []
        password = password or None
        preferred_auth = "password,keyboard-interactive"

    if known_hosts_file.is_file():
        known_hosts = str(known_hosts_file)
        trust_first_connection = False
    elif CONFIG.SFTP_TRUST_ON_FIRST_USE:
        known_hosts = None
        trust_first_connection = True
    else:
        raise RuntimeError(
            "SFTP host key is unknown and trust-on-first-use is disabled."
        )

    print()
    print("Connecting to SFTP server...")

    async with asyncssh.connect(
        host,
        port=port,
        username=username,
        password=password,
        known_hosts=known_hosts,
        client_keys=client_keys,
        passphrase=private_key_passphrase or None,
        preferred_auth=preferred_auth,
        agent_path=None,
        login_timeout=timeout,
    ) as connection:
        if trust_first_connection:
            save_asyncssh_host_key(
                connection,
                host,
                port,
                known_hosts_file,
            )
            print("SFTP server key saved for future verification.")

        async with connection.start_sftp_client() as sftp:
            public_dir = str(CONFIG.SFTP_REMOTE_PUBLIC_DIR)
            private_dir = str(CONFIG.SFTP_REMOTE_PRIVATE_DIR)

            if not await sftp.isdir(public_dir):
                raise RuntimeError(
                    f"Remote public directory does not exist: {public_dir}"
                )

            if not await sftp.isdir(private_dir):
                raise RuntimeError(
                    f"Remote private directory does not exist: {private_dir}"
                )

            uploads = configured_sftp_uploads()

            for local_path, remote_path in uploads:
                if not local_path.is_file():
                    raise RuntimeError(
                        f"Local export file is missing: {local_path}"
                    )

                print(f"Uploading {local_path.name}...")
                await replace_remote_file(
                    sftp,
                    local_path,
                    remote_path,
                )

    print("SFTP upload completed successfully.")


def sftp_batch_quote(value: str | Path) -> str:
    text = str(value).replace('"', '""')
    return f'"{text}"'


def upload_exports_openssh() -> None:
    validate_sftp_config()

    sftp_executable = shutil.which("sftp")

    if not sftp_executable:
        raise RuntimeError(
            "Windows OpenSSH SFTP was not found. Install the Windows "
            "OpenSSH Client optional feature or use password-based SFTP."
        )

    host = str(CONFIG.SFTP_HOST).strip()
    port = int(CONFIG.SFTP_PORT)
    username = str(CONFIG.SFTP_USERNAME).strip()
    private_key_file = str(CONFIG.SFTP_PRIVATE_KEY_FILE).strip()
    private_key_path = resolve_local_path(private_key_file)
    known_hosts_file = resolve_local_path(CONFIG.SFTP_KNOWN_HOSTS_FILE)

    if str(CONFIG.SFTP_PRIVATE_KEY_PASSPHRASE):
        raise RuntimeError(
            "The Windows OpenSSH batch upload cannot use a key passphrase "
            "directly. Load the key into ssh-agent or use an unencrypted "
            "dedicated SongSync key."
        )

    strict_host_checking = (
        "accept-new"
        if CONFIG.SFTP_TRUST_ON_FIRST_USE
        else "yes"
    )

    public_dir = str(CONFIG.SFTP_REMOTE_PUBLIC_DIR)
    private_dir = str(CONFIG.SFTP_REMOTE_PRIVATE_DIR)

    uploads = configured_sftp_uploads()

    batch_lines = [
        f"ls {sftp_batch_quote(public_dir)}",
        f"ls {sftp_batch_quote(private_dir)}",
    ]

    for local_path, remote_path in uploads:
        if not local_path.is_file():
            raise RuntimeError(
                f"Local export file is missing: {local_path}"
            )

        temporary_path = remote_path + ".tmp"
        batch_lines.extend(
            [
                (
                    f"put {sftp_batch_quote(local_path.resolve())} "
                    f"{sftp_batch_quote(temporary_path)}"
                ),
                f"-rm {sftp_batch_quote(remote_path)}",
                (
                    f"rename {sftp_batch_quote(temporary_path)} "
                    f"{sftp_batch_quote(remote_path)}"
                ),
            ]
        )

    batch_lines.append("quit")
    batch_input = "\n".join(batch_lines) + "\n"

    command = [
        sftp_executable,
        "-q",
        "-b",
        "-",
        "-P",
        str(port),
        "-i",
        str(private_key_path),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts_file}",
        "-o",
        f"StrictHostKeyChecking={strict_host_checking}",
        f"{username}@{host}",
    ]

    print()
    print("Connecting to SFTP server with Windows OpenSSH...")

    result = run_without_window(
        command,
        input=batch_input,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            "Windows OpenSSH SFTP upload failed"
            + (f":\n{details}" if details else ".")
        )

    print("SFTP upload completed successfully.")


def upload_exports_sftp() -> None:
    if not CONFIG.SFTP_ENABLED:
        print()
        print("SFTP upload is disabled.")
        return

    private_key_file = str(CONFIG.SFTP_PRIVATE_KEY_FILE).strip()

    if os.name == "nt" and private_key_file:
        upload_exports_openssh()
        return

    asyncio.run(upload_exports_async())


def catalog_hash(unique_songs: list[Song]) -> str:
    digest = hashlib.sha256()

    for song in unique_songs:
        row = (
            f"{song.track_id}\0{song.artist}\0{song.title}\0"
            f"{song.filename}\0{song.genre}\0{song.playcount}\0"
            f"{song.lastplayed}\0{'|'.join(song.play_history)}\n"
        )
        digest.update(row.encode("utf-8"))

    return digest.hexdigest()


def write_exports(
    all_songs: list[Song],
    usable_songs: list[Song],
    unique_songs: list[Song],
    duplicate_groups: dict[tuple[str, str], list[Song]],
) -> None:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    public_songs = [
        {
            "track_id": song.track_id,
            "artist": song.artist,
            "title": song.title,
            "plays": song.playcount,
            "last_played": song.lastplayed,
            "play_history": list(song.play_history),
        }
        for song in unique_songs
    ]

    private_lookup = {
        str(song.track_id): {
            "filename": song.filename,
        }
        for song in unique_songs
    }

    artists = sorted(
        {song.artist for song in unique_songs if song.artist},
        key=str.casefold,
    )

    genres = sorted(
        {song.genre for song in unique_songs if song.genre},
        key=str.casefold,
    )

    info = {
        "generator": "RadioBOSS SongSync Engine",
        "version": VERSION,
        "generated_at": generated_at,
        "database": database_label(),
        "database_records": len(all_songs),
        "usable_records": len(usable_songs),
        "unique_songs": len(unique_songs),
        "duplicate_records": len(usable_songs) - len(unique_songs),
        "duplicate_groups": len(duplicate_groups),
        "artists": len(artists),
        "genres": len(genres),
        "catalog_hash": catalog_hash(unique_songs),
    }

    atomic_json_write(SONGS_FILE, public_songs)
    atomic_json_write(LOOKUP_FILE, private_lookup)
    atomic_json_write(ARTISTS_FILE, artists)
    atomic_json_write(GENRES_FILE, genres)
    atomic_json_write(INFO_FILE, info)


def write_scheduler_events_export() -> dict | None:
    if not bool(getattr(CONFIG, "SCHEDULER_EXPORT_ENABLED", False)):
        return None

    configured_path = str(
        getattr(CONFIG, "SCHEDULER_SDL_FILE", "")
    ).strip()
    if not configured_path:
        raise RuntimeError(
            "SCHEDULER_SDL_FILE is required when scheduler export is enabled."
        )

    sdl_path = resolve_local_path(configured_path)
    payload = create_scheduler_payload(sdl_path, VERSION)
    atomic_json_write(SCHEDULER_EVENTS_FILE, payload)
    return payload


def write_duplicate_log(
    duplicate_groups: dict[tuple[str, str], list[Song]],
) -> None:
    DUPLICATE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DUPLICATE_LOG_FILE.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"RadioBOSS SongSync Engine v{VERSION}\n")
        handle.write("Duplicate report\n")
        handle.write("=" * 72 + "\n\n")

        for entries in duplicate_groups.values():
            kept = entries[0]

            handle.write(f"{kept.artist} - {kept.title}\n")
            handle.write(
                f"KEPT    Track ID {kept.track_id}: {kept.filename}\n"
            )

            for ignored in entries[1:]:
                handle.write(
                    f"IGNORED Track ID {ignored.track_id}: {ignored.filename}\n"
                )

            handle.write("\n")


def print_report(
    all_songs: list[Song],
    usable_songs: list[Song],
    unique_songs: list[Song],
    duplicate_groups: dict[tuple[str, str], list[Song]],
    scheduler_payload: dict | None,
) -> None:
    missing_filename = sum(1 for song in all_songs if not song.filename)
    missing_metadata = sum(
        1 for song in all_songs if not song.artist or not song.title
    )
    invalid = sum(
        1
        for song in all_songs
        if song.valid is not None and int(song.valid) == 0
    )
    disabled = sum(
        1
        for song in all_songs
        if song.disabled is not None and int(song.disabled) != 0
    )

    print()
    print("=" * 66)
    print(f"RadioBOSS SongSync Engine v{VERSION}")
    print("=" * 66)
    print(f"Database:                     {database_label()}")
    print(f"Database records:             {len(all_songs):>10}")
    print(f"Usable song records:          {len(usable_songs):>10}")
    print(f"Unique artist/title:          {len(unique_songs):>10}")
    print(f"Duplicate records ignored:    {len(usable_songs)-len(unique_songs):>10}")
    print(f"Duplicate groups:             {len(duplicate_groups):>10}")
    print(f"Missing filename:             {missing_filename:>10}")
    print(f"Missing artist/title:         {missing_metadata:>10}")
    print(f"Invalid records:              {invalid:>10}")
    print(f"Disabled records:             {disabled:>10}")
    print("=" * 66)

    if CONFIG.SHOW_EXAMPLES:
        limit = min(CONFIG.EXAMPLE_LIMIT, len(unique_songs))
        print()
        print(f"First {limit} public search entries:")
        print("-" * 66)

        for song in unique_songs[:limit]:
            print(f"{song.track_id:>8} | {song.artist} - {song.title}")

    print()
    print("Public files:")
    print(f"  {SONGS_FILE.resolve()}")
    print(f"  {ARTISTS_FILE.resolve()}")
    print(f"  {GENRES_FILE.resolve()}")
    print(f"  {INFO_FILE.resolve()}")
    print()
    print("Private files:")
    print(f"  {LOOKUP_FILE.resolve()}")
    print(f"  {DUPLICATE_LOG_FILE.resolve()}")
    if scheduler_payload is not None:
        print(f"  {SCHEDULER_EVENTS_FILE.resolve()}")
        print(
            "  Scheduler playlist events: "
            f"{int(scheduler_payload.get('event_count', 0))}"
        )
    print()
    print("Export completed. No RadioBOSS data was changed.")


def main() -> int:
    print(f"RadioBOSS SongSync Engine v{VERSION}")

    if CONFIG.DB_TYPE == "sqlite":
        print("Opening RadioBOSS SQLite database...")
    else:
        print("Connecting to RadioBOSS MySQL database...")

    connection = None

    try:
        connection = connect_database()

        if (
            CONFIG.DB_TYPE == "mysql"
            and not connection.is_connected()
        ):
            raise RuntimeError("MySQL connection was not established.")

        verify_required_tables(connection)

        print("Connection successful.")
        print("Reading tracks2 and taginfo...")

        all_songs = load_songs(connection)
        usable_songs = [song for song in all_songs if is_usable(song)]

        print("Creating unique song catalog...")
        unique_songs, duplicate_groups = create_unique_catalog(usable_songs)

        print("Writing public and private JSON files...")
        write_exports(
            all_songs,
            usable_songs,
            unique_songs,
            duplicate_groups,
        )
        write_duplicate_log(duplicate_groups)
        scheduler_payload = write_scheduler_events_export()

        print_report(
            all_songs,
            usable_songs,
            unique_songs,
            duplicate_groups,
            scheduler_payload,
        )

        upload_exports_sftp()

        return 0

    except MySQLError as exc:
        print()
        print("MYSQL ERROR:")
        print(exc)
        return 1

    except Exception as exc:
        print()
        print("ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    finally:
        if connection is not None:
            if CONFIG.DB_TYPE == "sqlite":
                connection.close()
            elif connection.is_connected():
                connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
