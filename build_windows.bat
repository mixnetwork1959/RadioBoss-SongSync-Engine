@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BUILD_VENV=%CD%\.songsync-build-venv"
set "BUILD_PYTHON=%BUILD_VENV%\Scripts\python.exe"

echo ==========================================================
echo RadioBOSS SongSync Engine v1.8.0 - Windows Build
echo ==========================================================
echo.

echo [1/9] Selecting a Python installation with working Tkinter...
set "PY_SELECTOR="

py -3.14 -c "import tkinter; t=tkinter.Tcl(); print(t.call('info','patchlevel'))" >nul 2>&1
if not errorlevel 1 set "PY_SELECTOR=-3.14"

if not defined PY_SELECTOR (
  py -3.13 -c "import tkinter; t=tkinter.Tcl(); print(t.call('info','patchlevel'))" >nul 2>&1
  if not errorlevel 1 set "PY_SELECTOR=-3.13"
)

if not defined PY_SELECTOR (
  py -3.12 -c "import tkinter; t=tkinter.Tcl(); print(t.call('info','patchlevel'))" >nul 2>&1
  if not errorlevel 1 set "PY_SELECTOR=-3.12"
)

if not defined PY_SELECTOR goto :python_error
echo Using Python %PY_SELECTOR%

echo.
echo [2/9] Creating a clean build environment...
if exist "%BUILD_VENV%" rmdir /s /q "%BUILD_VENV%"
py %PY_SELECTOR% -m venv "%BUILD_VENV%"
if errorlevel 1 goto :error

echo.
echo [3/9] Installing build and runtime dependencies...
"%BUILD_PYTHON%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error
"%BUILD_PYTHON%" -m pip install --upgrade --force-reinstall -r requirements.txt
if errorlevel 1 goto :error
"%BUILD_PYTHON%" -m pip install --upgrade --force-reinstall pyinstaller==6.22.2
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [4/9] Building a Tkinter onefile smoke test...
"%BUILD_PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name SongSync-Tk-Smoke-Test ^
  tkinter_bundle_smoke_test.py
if errorlevel 1 goto :tk_bundle_error

echo.
echo [5/9] Running the bundled Tkinter smoke test...
"dist\SongSync-Tk-Smoke-Test.exe"
if errorlevel 1 goto :tk_bundle_error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SongSync-Tk-Smoke-Test.spec del /q SongSync-Tk-Smoke-Test.spec

echo.
echo [6/9] Building normal SongSync executable...
"%BUILD_PYTHON%" -m PyInstaller ^
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
  --hidden-import config_store ^
  --hidden-import sftp_host_keys ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync ^
  songsync_launcher.py
if errorlevel 1 goto :error

echo.
echo [7/9] Building Setup Wizard...
"%BUILD_PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --collect-all mysql.connector ^
  --collect-submodules mysql.connector.plugins ^
  --collect-submodules mysql.connector.aio ^
  --collect-all asyncssh ^
  --hidden-import setup_wizard ^
  --hidden-import config_store ^
  --hidden-import sftp_host_keys ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync-Setup ^
  setup_launcher.py
if errorlevel 1 goto :error

echo.
echo [8/9] Building debug executable...
"%BUILD_PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --collect-all mysql.connector ^
  --collect-submodules mysql.connector.plugins ^
  --collect-submodules mysql.connector.aio ^
  --collect-all asyncssh ^
  --hidden-import setup_wizard ^
  --hidden-import scheduler_export ^
  --hidden-import config_store ^
  --hidden-import sftp_host_keys ^
  --hidden-import mysql.connector.plugins.mysql_native_password ^
  --hidden-import mysql.connector.plugins.caching_sha2_password ^
  --hidden-import mysql.connector.plugins.sha256_password ^
  --name RadioBOSS-SongSync-Debug ^
  songsync.py
if errorlevel 1 goto :error

echo.
echo [9/9] Verifying build output...
if not exist "dist\RadioBOSS-SongSync.exe" goto :output_error
if not exist "dist\RadioBOSS-SongSync-Setup.exe" goto :output_error
if not exist "dist\RadioBOSS-SongSync-Debug.exe" goto :output_error

echo.
echo ==========================================================
echo Build completed and Tkinter onefile test passed
echo ==========================================================
echo.
echo Copy these three files from dist to the SongSync folder:
echo   RadioBOSS-SongSync.exe
echo   RadioBOSS-SongSync-Setup.exe
echo   RadioBOSS-SongSync-Debug.exe
echo.
exit /b 0

:python_error
echo.
echo ERROR: Python 3.12, 3.13 or 3.14 with Tkinter was not found.
echo Install a normal 64-bit Python release including Tcl/Tk support.
goto :failed

:tk_bundle_error
echo.
echo ERROR: The bundled Tkinter onefile smoke test failed.
echo Do not copy this build to the RadioBOSS computer.
goto :failed

:output_error
echo.
echo ERROR: One or more expected executable files are missing.
goto :failed

:error
echo.
echo ERROR: The Windows build command failed.

:failed
echo.
echo ==========================================================
echo BUILD FAILED
echo ==========================================================
pause
exit /b 1
