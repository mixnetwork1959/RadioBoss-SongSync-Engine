# RadioBOSS SongSync Engine – Installation Guide

This guide explains how to install RadioBOSS SongSync Engine, connect it to a RadioBOSS SQLite or MySQL/MariaDB library and create the first JSON catalog.

For SFTP configuration, see:

[SFTP Setup Guide](SFTP_SETUP.md)

For automatic daily execution, see:

[RadioBOSS Automation Guide](RADIOBOSS_AUTOMATION.md)

## Requirements

- Windows 10 or Windows 11
- RadioBOSS using its standard SQLite library or MySQL/MariaDB
- Read access to the selected RadioBOSS database
- Internet access for optional SFTP uploads

The recommended Windows EXE does not require Python.

Python 3.10 or newer is required only when running SongSync from
the source code.

SongSync reads these RadioBOSS database tables:

```text
tracks2
taginfo
```

SongSync never modifies the RadioBOSS database.

## 1. Download SongSync

Download the latest release from:

https://github.com/mixnetwork1959/RadioBOSS-SongSync-Engine/releases

Choose one of these downloads:

- `RadioBOSS-SongSync-v1.7.2.zip` for the recommended
  Windows EXE
- Source code for users who want to run SongSync with Python

Extract the selected ZIP file to a permanent directory.

Example:

```text
D:\radioboss-song-sync
```

Do not run SongSync directly from the Downloads folder or from inside the ZIP archive.

## 2. Windows EXE installation (recommended)

The Windows package includes:

```text
RadioBOSS-SongSync.exe
config.example.py
run_songsync.bat
README.md
LICENSE
docs\
```

No Python installation and no additional Python packages are
required.

Continue with:

[Create the private configuration](#4-create-the-private-configuration)

## Optional private scheduler export

Radio Music Analytics cannot access the RadioBOSS computer directly. SongSync
can bridge that gap by reading the local scheduler file and uploading a
sanitized private JSON file.

In the Setup Wizard, enable “Export playlist events for Radio Music
Analytics”, then select the active RadioBOSS `.sdl` file. With manual
configuration use:

```python
SCHEDULER_EXPORT_ENABLED = True
SCHEDULER_SDL_FILE = r"C:\path\to\RadioBOSS\Admin.sdl"
```

The resulting `exports/private/scheduler-events.json` contains playlist-event
metadata but no complete Windows paths. When SFTP is enabled, SongSync uploads
it to the configured private remote directory.

## 3. Python source installation

This section is required only when running `songsync.py` instead
of the Windows EXE.

### Check Python

Open a command prompt and run:

```bat
py --version
```

Expected result:

```text
Python 3.10 or newer
```

If the `py` command is unavailable, install Python from:

https://www.python.org/downloads/

During installation, enable:

```text
Add Python to PATH
```

### Install required packages

Open a command prompt in the SongSync directory:

```bat
cd /d D:\radioboss-song-sync
```

Install the required Python packages:

```bat
py -m pip install -r requirements.txt
```

The requirements are:

```text
mysql-connector-python>=9.0,<10.0
asyncssh>=2.20
```

To confirm installation:

```bat
py -m pip show mysql-connector-python
py -m pip show asyncssh
```

## 4. Create the private configuration

Copy:

```text
config.example.py
```

to:

```text
config.py
```

Do not rename or delete `config.example.py`. It is the public template.

The new `config.py` is the private local configuration.

> [!WARNING]
> Never upload `config.py` to GitHub, a website, a forum or a chat message.

## 5. Configure the RadioBOSS MySQL connection

Open `config.py` in a text editor.

Enter the RadioBOSS MySQL settings:

```python
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "radioboss"
DB_USER = "radioboss_readonly"
DB_PASSWORD = "CHANGE_ME"
DB_CHARSET = "utf8mb4"
```

Replace the example values with the real MySQL settings.

### DB_HOST

Use:

```python
DB_HOST = "127.0.0.1"
```

when SongSync runs on the same computer as the RadioBOSS MySQL server.

For a remote MySQL server, enter its hostname or IP address.

### DB_PORT

The standard MySQL port is:

```python
DB_PORT = 3306
```

Only change it if the MySQL server uses another port.

### DB_NAME

Enter the database containing the RadioBOSS tables.

Example:

```python
DB_NAME = "radioboss"
```

### DB_USER and DB_PASSWORD

A dedicated read-only MySQL user is strongly recommended.

The user requires permission to read:

```text
tracks2
taginfo
```

SongSync does not require permission to insert, update or delete records.

### DB_CHARSET

Keep:

```python
DB_CHARSET = "utf8mb4"
```

This allows international artist names, titles and characters.

## 6. Configure local export directories

The default settings are:

```python
PUBLIC_EXPORT_DIR = "exports/public"
PRIVATE_EXPORT_DIR = "exports/private"
```

These paths are relative to the SongSync directory.

With the example installation directory, SongSync creates:

```text
D:\radioboss-song-sync\exports\public
D:\radioboss-song-sync\exports\private
```

The directories are created automatically.

## 7. Configure console examples

The default settings are:

```python
SHOW_EXAMPLES = True
EXAMPLE_LIMIT = 10
```

When enabled, SongSync displays the first ten public catalog entries after an export.

To disable examples:

```python
SHOW_EXAMPLES = False
```

## 8. Keep SFTP disabled for the first test

Before the first local test, use:

```python
SFTP_ENABLED = False
```

This ensures that SongSync creates the files locally without uploading anything.

## 9. Run the first local export

### Windows EXE

From the SongSync directory, run:

```bat
run_songsync.bat
```

You can also start the executable directly:

```bat
RadioBOSS-SongSync.exe
```

### Python source version

```bat
py songsync.py
```

A normal start looks similar to:

```text
RadioBOSS SongSync Engine v1.7.2
Database: <selected SQLite or MySQL/MariaDB database>
Connecting to RadioBOSS database...
Connection successful.
Reading tracks2 and taginfo...
Creating unique song catalog...
Writing public and private JSON files...
```

A successful local export ends with:

```text
Export completed. No RadioBOSS data was changed.

SFTP upload is disabled.
```

## 10. Verify generated files

Check:

```text
exports\public
```

It must contain:

```text
songs.json
artists.json
genres.json
info.json
```

Check:

```text
exports\private
```

It must contain:

```text
lookup.json
duplicates.log
```

## 11. Understand the generated files

### songs.json

Contains the public search catalog:

```json
[
  {
    "track_id": 11698,
    "artist": "2pac",
    "title": "Dear Mama",
    "plays": 42,
    "last_played": "2026-08-05 13:42:17",
    "play_history": [
      "2026-08-05 13:42:17",
      "2026-08-04 09:11:02"
    ]
  }
]
```

It does not contain local music paths.

### artists.json

Contains a sorted list of artists.

### genres.json

Contains a sorted list of genres.

### info.json

Contains export information, including:

- Generator version
- Export time
- Database record count
- Usable record count
- Unique song count
- Duplicate count
- Artist count
- Genre count
- Catalog hash

### lookup.json

Contains the private connection between a track ID and the real RadioBOSS filename.

Example:

```json
{
  "11698": {
    "filename": "D:\\Music\\Pop\\2pac - Dear Mama.mp3"
  }
}
```

This file must be uploaded only to the protected private website directory.

### duplicates.log

Lists duplicate artist/title combinations.

The first matching track is retained in the public catalog. Other matching tracks are listed in the report.

SongSync does not delete duplicate files.

## 12. Verify catalog statistics

The console report includes:

```text
Database records
Usable song records
Unique artist/title
Duplicate records ignored
Duplicate groups
Missing filename
Missing artist/title
Invalid records
Disabled records
```

A difference between database records and unique songs is normal.

Reasons include:

- Duplicate artist/title combinations
- Missing artist or title
- Invalid tracks
- Disabled tracks

## 13. Configure SFTP

After the local export works, continue with:

[SFTP Setup Guide](SFTP_SETUP.md)

Do not enable SFTP before the local export has completed successfully.

## 14. Configure automatic execution

After the local export and SFTP upload both work, continue with:

[RadioBOSS Automation Guide](RADIOBOSS_AUTOMATION.md)

## Updating SongSync

Before updating:

1. Keep a private backup of `config.py`.
2. Keep a private backup of the SSH private key when used.
3. Download the new release.
4. Replace `RadioBOSS-SongSync.exe` or the Python source files.
5. Do not overwrite the working `config.py`.
6. Run a manual test before relying on the scheduled event.

Private files are not included in release downloads.

## Troubleshooting

### config.py was not found

Error:

```text
ERROR: config.py was not found.
```

Solution:

Copy:

```text
config.example.py
```

to:

```text
config.py
```

Then enter the real settings.

### mysql-connector-python is not installed

This message applies only to the Python source version.

Run:

```bat
py -m pip install -r requirements.txt
```

### MySQL connection failed

Check:

- MySQL server is running
- Hostname or IP address
- Port
- Database name
- Username
- Password
- Firewall
- User permissions

### Required RadioBOSS tables are missing

SongSync requires:

```text
tracks2
taginfo
```

Confirm that `DB_NAME` points to the correct RadioBOSS database.

### No songs are exported

Check that tracks contain:

- Filename
- Artist
- Title

Also check that tracks are not marked invalid or disabled.

### SFTP upload is disabled

This is normal when:

```python
SFTP_ENABLED = False
```

Complete the local export test first, then configure SFTP.

### Private files appeared in GitHub Desktop

Do not commit.

Confirm that `.gitignore` contains:

```gitignore
config.py
exports/
sftp_key
sftp_key.pub
sftp_known_hosts
```

## Security checklist

Before publishing or requesting support:

- Remove database passwords
- Remove SFTP passwords
- Never send the private SSH key
- Never publish `config.py`
- Never publish `lookup.json`
- Never publish complete local music paths
- Never publish the SFTP known-hosts file
