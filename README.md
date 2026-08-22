# RadioBOSS SongSync Engine

**Version 1.7.2**

RadioBOSS SongSync Engine reads the RadioBOSS music library from its standard SQLite database or from MySQL/MariaDB and generates secure JSON catalog files for the [RadioBOSS Song Request System](https://github.com/mixnetwork1959/radioboss-song-request-system).

It can automatically upload the generated catalog to a web server using SFTP.

> [!IMPORTANT]
> SongSync does not modify the RadioBOSS database.
> It only reads music-library information and creates export files.


## Setup Wizard

Version 1.7.2 includes a separate Windows setup application:

```text
RadioBOSS-SongSync-Setup.exe
```

The setup application is built with no console window. It configures the database, exports and optional SFTP upload.

`RadioBOSS-SongSync.exe` remains the normal console synchronization executable so it can still be used reliably from RadioBOSS events, Task Scheduler and log files.


## Windows executables in v1.7.2

The Windows build creates three executables:

```text
RadioBOSS-SongSync.exe
RadioBOSS-SongSync-Setup.exe
RadioBOSS-SongSync-Debug.exe
```

### RadioBOSS-SongSync.exe

Normal synchronization executable.

- No CMD/console window
- Intended for normal use and RadioBOSS Scheduler events
- Writes runtime output to `songsync.log`
- Rotates a large log to `songsync-old.log`

### RadioBOSS-SongSync-Setup.exe

Graphical configuration wizard.

- No CMD/console window
- Configures SQLite or MySQL/MariaDB
- Tests the database connection
- Configures and tests SFTP
- Creates the local `config.py`

### RadioBOSS-SongSync-Debug.exe

Console version for troubleshooting.

It performs the same synchronization but leaves the console visible so error output can be inspected directly.


## Windows EXE installation (recommended)

Windows users can run SongSync without installing Python or additional packages.

1. Download `RadioBOSS-SongSync-v1.7.2.zip` from the latest GitHub release.
2. Extract the ZIP file to a permanent directory, for example:

   ```text
   C:\RadioBOSS-SongSync
   ```

3. Start:

   ```text
   RadioBOSS-SongSync.exe
   ```

   On the first start, SongSync automatically creates `config.py` from
   `config.example.py` and then exits.

4. Open `config.py` and select SQLite or MySQL/MariaDB. Enter the optional SFTP settings when automatic upload is required.
5. If SSH key authentication is used, place the private key in the same directory and configure:

   ```python
   SFTP_PRIVATE_KEY_FILE = "sftp_key"
   ```

6. Start SongSync again:

   ```text
   RadioBOSS-SongSync.exe
   ```

The generated catalog files are written to the local `exports` directory. If SFTP is enabled, the files are uploaded automatically after a successful export.

Python is not required for the Windows EXE version.

### Private files

Never publish or share these files:

- `config.py`
- `sftp_key`
- `sftp_key.pub`
- `sftp_known_hosts`
- files generated inside `exports`

## Companion project

SongSync is designed to work with:

[RadioBOSS Song Request System](https://github.com/mixnetwork1959/radioboss-song-request-system)

Both projects are required for the complete web-based request system:

1. SongSync reads the RadioBOSS music library.
2. SongSync generates public and private JSON files.
3. The files are uploaded to the web server.
4. The request website uses the files for search and secure requests.
5. Requested songs are sent to RadioBOSS through its Remote Control API.

## Features

- Reads the standard RadioBOSS SQLite music library
- Automatically finds shared or dedicated RadioBOSS SQLite databases
- Supports MySQL/MariaDB as an alternative database
- Opens SQLite databases in read-only mode
- Uses the `tracks2` and `taginfo` tables
- Excludes invalid or disabled tracks
- Excludes tracks without artist, title or filename
- Removes duplicate artist/title combinations
- Creates a public song catalog
- Exports play count, last-played time and play history for each song
- Creates artist and genre lists
- Creates catalog information and statistics
- Creates a private RadioBOSS filename lookup
- Creates a duplicate report
- Reads a selected local RadioBOSS `.sdl` scheduler file when enabled
- Detects music blocks without relying on event names or language
- Creates a private, path-safe scheduler-event export for rotation analytics
- Writes JSON files atomically
- Supports automatic SFTP uploads
- Supports SFTP password authentication
- Supports SSH private-key authentication
- Uses Windows OpenSSH automatically for private-key uploads on Windows
- Verifies the SFTP server identity
- Keeps database and SFTP credentials private
- Can be started automatically from the RadioBOSS Scheduler

## Generated files

### Public files

The following files may be uploaded to the public web directory:

```text
exports/public/songs.json
exports/public/artists.json
exports/public/genres.json
exports/public/info.json
```

`songs.json` contains:

- Track ID
- Artist
- Title
- Play count
- Last-played time
- Play history

Example:

```json
[
  {
    "track_id": 1234,
    "artist": "Example Artist",
    "title": "Example Title",
    "plays": 42,
    "last_played": "2026-08-05 13:42:17",
    "play_history": [
      "2026-08-05 13:42:17",
      "2026-08-04 09:11:02"
    ]
  }
]
```

### Private files

The following files contain private information:

```text
exports/private/lookup.json
exports/private/duplicates.log
exports/private/scheduler-events.json
```

`lookup.json` connects a public track ID to the real RadioBOSS filename.

Example:

```json
{
  "1234": {
    "filename": "D:\\Music\\Example Artist - Example Title.mp3"
  }
}
```

> [!WARNING]
> `lookup.json` contains local music paths and must never be publicly downloadable.

`scheduler-events.json` is optional. It contains only sanitized playlist-event
metadata: the event name, schedule, action type and a path-safe preset or
playlist label. Complete local Windows paths are never written to this file.

Enable it in the Setup Wizard or in `config.py`:

```python
SCHEDULER_EXPORT_ENABLED = True
SCHEDULER_SDL_FILE = r"C:\path\to\RadioBOSS\Admin.sdl"
```

SongSync recognizes `generate`, `getrandomplaylist`, loaded M3U/M3U8/PLS files
and direct playlist-file events. It ignores non-music scheduler actions and
does not depend on names such as Morning, Night or any particular language.

## Requirements

### Windows EXE

- Windows 10 or Windows 11
- RadioBOSS using SQLite or MySQL/MariaDB
- Read access to the selected RadioBOSS database
- Internet access for optional SFTP uploads

### Python source version

- Python 3.10 or newer

Required Python packages:

```text
asyncssh>=2.20
```

MySQL/MariaDB additionally requires:

```text
mysql-connector-python>=9.0,<10.0
```

## Installation

Clone or download this repository.

Open a command prompt in the project directory and install the required packages:

```bat
py -m pip install -r requirements.txt
```

On the first start, SongSync copies `config.example.py` to `config.py`.
Enter the database selection and optional SFTP settings in `config.py`, then
start SongSync again.

> [!IMPORTANT]
> Never upload `config.py` to GitHub. It contains private credentials.

For complete setup instructions, see:

[Installation Guide](docs/INSTALLATION.md)

## SQLite configuration

SQLite is the default and recommended option for a standard RadioBOSS
installation:

```python
DB_TYPE = "sqlite"
SQLITE_MODE = "dedicated"
SQLITE_DATABASE = "auto"
```

Choose `dedicated` when RadioBOSS stores `tracks.db` inside its profile folder:

```text
%APPDATA%\djsoft.net\RadioBOSS_*\tracks.db
```

Choose `shared` when RadioBOSS uses the common database:

```python
SQLITE_MODE = "shared"
```

```text
%APPDATA%\djsoft.net\tracks.db
```

With `SQLITE_DATABASE = "auto"`, the Windows username and RadioBOSS profile
number do not need to be entered. If multiple dedicated databases are found,
SongSync lists them and asks for the required full path in
`SQLITE_DATABASE`.

## MySQL/MariaDB configuration

Set:

```python
DB_TYPE = "mysql"
```

Example:

```python
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "radioboss"
DB_USER = "radioboss_readonly"
DB_PASSWORD = "CHANGE_ME"
DB_CHARSET = "utf8mb4"
```

A dedicated read-only MySQL/MariaDB user is strongly recommended.

The MySQL user requires read access to:

```text
tracks2
taginfo
```

SongSync does not insert, update or delete any database records.

## Local export configuration

```python
PUBLIC_EXPORT_DIR = "exports/public"
PRIVATE_EXPORT_DIR = "exports/private"
```

The directories are created automatically when SongSync runs.

## Console configuration

```python
SHOW_EXAMPLES = True
EXAMPLE_LIMIT = 10
```

When enabled, SongSync displays a small selection of public catalog entries after an export.

## Running SongSync

Windows EXE:

```text
RadioBOSS-SongSync.exe
```

Python source version:

```bat
py songsync.py
```

A successful local export ends with:

```text
Export completed. No RadioBOSS data was changed.
```

If automatic SFTP upload is disabled, SongSync displays:

```text
SFTP upload is disabled.
```

## Automatic SFTP upload

Enable automatic upload in `config.py`:

```python
SFTP_ENABLED = True
```

Basic SFTP settings:

```python
SFTP_HOST = "your-sftp-server.example"
SFTP_PORT = 22

SFTP_USERNAME = "CHANGE_ME"
SFTP_PASSWORD = "CHANGE_ME"
```

Remote target directories:

```python
SFTP_REMOTE_PUBLIC_DIR = (
    "/path/to/songrequest/data/public"
)

SFTP_REMOTE_PRIVATE_DIR = (
    "/path/to/songrequest/data/private"
)
```

Both remote directories must already exist.

After a successful export, SongSync uploads:

```text
songs.json
artists.json
genres.json
info.json
lookup.json
```

When scheduler export is enabled, `scheduler-events.json` is also uploaded to
`SFTP_REMOTE_PRIVATE_DIR`. Radio Music Analytics can read it there without any
access to the RadioBOSS computer's filesystem.

A successful upload ends with:

```text
SFTP upload completed successfully.
```

## SSH private-key authentication

Some web hosts may reject automated password authentication even when the same credentials work in graphical SFTP programs.

SongSync therefore supports SSH private-key authentication.

Example:

```python
SFTP_PRIVATE_KEY_FILE = "sftp_key"
SFTP_PRIVATE_KEY_PASSPHRASE = ""
```

Leave the passphrase empty when the private key is not encrypted.

The private key must remain on the SongSync computer.

Never upload it to:

- GitHub
- The public website
- The web server
- A support forum
- A chat message

For detailed SFTP and SSH-key instructions, see:

[SFTP Setup Guide](docs/SFTP_SETUP.md)

## SFTP server verification

SongSync can trust the SFTP server key during the first successful connection:

```python
SFTP_TRUST_ON_FIRST_USE = True
SFTP_KNOWN_HOSTS_FILE = "sftp_known_hosts"
```

The first connection stores the server identity locally.

Future connections verify that the server presents the same key. If the key changes unexpectedly, SongSync stops the upload.

## Automatic RadioBOSS Scheduler event

SongSync can run automatically from the RadioBOSS Scheduler.

Create:

```text
run_songsync.bat
```

Example:

```bat
@echo off
cd /d "%~dp0"

if exist "RadioBOSS-SongSync.exe" (
    RadioBOSS-SongSync.exe
) else (
    py songsync.py
)
```

RadioBOSS scheduler command:

```text
run D:\radioboss-song-sync\run_songsync.bat
```

For example, the event can run once per day after the regular RadioBOSS database backup.

For detailed instructions, see:

[RadioBOSS Automation Guide](docs/RADIOBOSS_AUTOMATION.md)

## Security

The included `.gitignore` prevents private and generated files from being committed.

The following files must remain local:

```text
config.py
sftp_key
sftp_key.pub
sftp_known_hosts
exports/
```

Before every GitHub commit, verify that these files do not appear in the changes list.

## Recommended `.gitignore`

```gitignore
# Private configuration
config.py

# Generated exports
exports/

# SFTP credentials and server identity
sftp_key
sftp_key.pub
sftp_known_hosts

# Python cache
__pycache__/
*.py[cod]

# Virtual environments
.venv/
venv/

# Logs
logs/
*.log

# Editors
.vscode/
.idea/

# Windows
Thumbs.db
Desktop.ini

# PyInstaller
build/
dist/
*.spec
*.exe
```

## Duplicate handling

SongSync considers tracks duplicates when their normalized artist and title are identical.

The first matching RadioBOSS track is retained in the public catalog. Additional matching tracks are written to:

```text
exports/private/duplicates.log
```

Duplicate files are not deleted and the RadioBOSS database is not changed.

## Error behavior

If the selected database cannot be opened:

- No new catalog is uploaded
- Existing website files remain unchanged

If the local export fails:

- SFTP upload does not start
- Existing website files remain unchanged

If the SFTP upload fails:

- Local export files remain available
- Existing successfully uploaded website files remain available
- SongSync exits with an error message

## Typical workflow

```text
RadioBOSS SQLite or MySQL/MariaDB library
        |
        v
RadioBOSS SongSync Engine
        |
        +-- Public JSON catalog
        |
        +-- Private filename lookup
        |
        v
Encrypted SFTP upload
        |
        v
RadioBOSS Song Request System
```

## Project files

```text
RadioBOSS-SongSync-Engine/
|
|-- docs/
|   |-- INSTALLATION.md
|   |-- SFTP_SETUP.md
|   `-- RADIOBOSS_AUTOMATION.md
|
|-- .gitignore
|-- config.example.py
|-- LICENSE
|-- README.md
|-- requirements.txt
|-- run_songsync.bat
`-- songsync.py
```

Private and generated files are not included in the repository.

## Current versions

```text
SongSync Engine:              1.7.2
SQLite support:               Built into Python
MySQL connector (optional):   9.x
SFTP library:                 AsyncSSH 2.20 or newer
```

## License

This project is released under the MIT License.

See [LICENSE](LICENSE) for details.

## Feedback and issues

Bug reports, compatibility reports and suggestions are welcome through GitHub Issues.

When reporting an error, never include:

- Database passwords
- SFTP passwords
- Private SSH keys
- Full private configuration files
- Local music paths
