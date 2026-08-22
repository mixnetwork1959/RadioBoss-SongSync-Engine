# Changelog

## 1.7.2

- Prevented the Windows OpenSSH `sftp.exe` child process from opening a CMD
  window during automatic uploads.
- Reused the same hidden-window process options for live uploads and Setup
  Wizard connection tests.
- Added regression tests for Windows and non-Windows subprocess options.

## 1.7.0

- Added an optional local RadioBOSS `.sdl` scheduler export.
- Added detection for `generate`, `getrandomplaylist`, loaded playlists and
  direct M3U/M3U8/PLS playlist events.
- Added path-safe `scheduler-events.json` output without complete local paths.
- Added optional upload of the scheduler file to the private SFTP directory.
- Added Setup Wizard controls for enabling the export and selecting the SDL.
- Added unit tests and GitHub validation for scheduler parsing.
- Kept the scheduler feature disabled by default for existing installations.

## 1.6.0

- Added graphical Windows Setup Wizard.
- Added automatic SQLite database detection.
- Added SQLite and MySQL/MariaDB connection tests.
- Added guided SFTP configuration and connection test.
- Added password and SSH private-key authentication setup.
- Updated MySQL Connector packaging for PyInstaller compatibility.
- Normal `RadioBOSS-SongSync.exe` now runs without a CMD window.
- Normal runs write status and errors to `songsync.log`.
- Added automatic log rotation to `songsync-old.log`.
- Added `RadioBOSS-SongSync-Debug.exe` for console troubleshooting.
- Kept manual `config.example.py` configuration fully supported.

# Changelog

## v1.5.0

- Added improved Windows OpenSSH support for SSH private-key SFTP uploads.
- Improved compatibility with RadioBOSS SQLite shared and dedicated databases.
- Added `plays` to every public song record from `tracks2.playcount`.
- Added `last_played` from `tracks2.lastplayed`.
- Added `play_history` from `tracks2.lastplayedhistory` as a JSON array.
- Included airplay data in the catalog hash so changes trigger a fresh export/upload.
- Prepared SongSync data for automatic charts and future rotation analysis.
- Updated generic installation, SFTP and automation documentation.
- Kept hosting-provider-specific guidance optional; STRATO is documented only as an example.
