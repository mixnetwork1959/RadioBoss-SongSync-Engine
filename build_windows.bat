@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo RadioBOSS SongSync Engine v1.7.2 - Final Build
echo ==========================================================
echo.

echo [1/6] Updating build tools...
py -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error

echo.
echo [2/6] Installing runtime dependencies...
py -m pip install --upgrade --force-reinstall -r requirements.txt
if errorlevel 1 goto :error

echo.
echo [3/6] Installing PyInstaller 6.21.0...
py -m pip install --upgrade --force-reinstall pyinstaller==6.21.0
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [4/6] Building normal SongSync executable (no CMD window)...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --collect-all mysql.connector ^
  --collect-submodules mysql.connector.plugins ^
  --collect-submodules mysql.connector.aio ^
  --collect-all asyncssh ^
  --hidden-import setup_wizard ^
  --hidden-import scheduler_export ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync ^
  songsync_launcher.py
if errorlevel 1 goto :error

echo.
echo [5/6] Building Setup Wizard (no CMD window)...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --collect-all mysql.connector ^
  --collect-submodules mysql.connector.plugins ^
  --collect-submodules mysql.connector.aio ^
  --collect-all asyncssh ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync-Setup ^
  setup_launcher.py
if errorlevel 1 goto :error

echo.
echo [6/6] Building SongSync debug executable (CMD window)...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --collect-all mysql.connector ^
  --collect-submodules mysql.connector.plugins ^
  --collect-submodules mysql.connector.aio ^
  --collect-all asyncssh ^
  --hidden-import setup_wizard ^
  --hidden-import scheduler_export ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync-Debug ^
  songsync.py
if errorlevel 1 goto :error

echo.
echo ==========================================================
echo Build completed
echo ==========================================================
echo.
echo Normal synchronization - no CMD window:
echo   dist\RadioBOSS-SongSync.exe
echo.
echo Setup Wizard - no CMD window:
echo   dist\RadioBOSS-SongSync-Setup.exe
echo.
echo Debug synchronization - CMD window:
echo   dist\RadioBOSS-SongSync-Debug.exe
echo.
echo Normal runs write output to:
echo   songsync.log
echo.
exit /b 0

:error
echo.
echo ==========================================================
echo BUILD FAILED
echo ==========================================================
pause
exit /b 1
