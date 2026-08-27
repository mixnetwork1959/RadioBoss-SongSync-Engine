# SongSync 1.8.0 – SFTP- und Setup-Fix

## Windows-EXE bauen

`build_windows.bat` per Doppelklick starten. Das Skript verwendet eine saubere
Build-Umgebung mit PyInstaller 6.22.2. Vor den eigentlichen Programmen baut und
startet es eine kleine Ein-Datei-Tkinter-Test-EXE. Dadurch werden sowohl
klassische als auch eingebettete Tcl/Tk-Daten geprüft. Nur wenn am Ende
`Build completed and Tkinter onefile test passed` steht, dürfen die EXE-Dateien
aus `dist` verwendet werden.

## Behobene Probleme

- Das Setup speichert jetzt ausschließlich `config.json`.
- Eine vorhandene `config.json` wird beim Speichern wirklich ersetzt.
- Vor dem Ersetzen entsteht automatisch `config.json.bak`.
- Eine alte `config.py` wird einmalig importiert, wenn noch keine
  `config.json` vorhanden ist.
- SSH-Key-Uploads verwenden unter Windows direkt die mitgelieferte
  AsyncSSH-Bibliothek. Windows OpenSSH ist nicht mehr erforderlich.
- `sftp_known_hosts` wird nach der ersten erfolgreichen, vertrauten Anmeldung
  automatisch neben der SongSync-EXE angelegt.
- Relative Pfade wie `sftp_key` werden immer relativ zum Verzeichnis der
  SongSync-EXE aufgelöst.

## Update auf dem RadioBOSS-Rechner

1. RadioBOSS Toolkit und SongSync schließen.
2. Nur diese drei neuen Dateien nach
   `D:\RadioBOSS Toolkit\tools\SongSync` kopieren:
   - `RadioBOSS-SongSync.exe`
   - `RadioBOSS-SongSync-Debug.exe`
   - `RadioBOSS-SongSync-Setup.exe`
3. Vorhandene Dateien wie `config.json`, `sftp_key` und `exports` nicht
   löschen oder durch Dateien aus einem Update-Paket ersetzen.
4. `RadioBOSS-SongSync-Setup.exe` starten.
5. SFTP aktivieren und `sftp_key` als privaten Schlüssel auswählen. Liegt die
   Datei direkt neben der EXE, wird sie automatisch vorgeschlagen.
6. „Trust server key on first successful connection“ aktiviert lassen.
7. „Test SFTP connection“ ausführen. Bei Erfolg entsteht automatisch
   `sftp_known_hosts`.
8. „Save configuration“ anklicken. Die bisherige JSON-Datei steht danach als
   `config.json.bak` bereit.
9. `RadioBOSS-SongSync-Debug.exe` einmal starten und auf
   `SFTP upload completed successfully.` achten.

Private Dateien (`config.json`, `config.json.bak`, `sftp_key` und
`sftp_known_hosts`) niemals hochladen oder weitergeben.
