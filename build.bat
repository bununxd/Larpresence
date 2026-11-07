@echo off
cd /d "%~dp0"
title Building Larpresence

if not exist larpresence.py (
  echo ERROR: larpresence.py was not found next to build.bat.
  goto fail
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found. Install Python 3.9 or newer from python.org and tick "Add python.exe to PATH".
  goto fail
)

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto fail
)
call .venv\Scripts\activate.bat

echo Installing requirements...
python -m pip install --quiet -r requirements.txt pyinstaller
if errorlevel 1 goto fail

echo Building the exe, this takes a minute...
pyinstaller --noconfirm --clean --onefile --windowed --icon icon.ico --name Larpresence --hidden-import pystray._win32 larpresence.py
if not exist dist\Larpresence.exe goto fail

echo.
echo ===== Done. Your exe is dist\Larpresence.exe =====
pause
exit /b 0

:fail
echo.
echo ===== BUILD FAILED. Read the messages above. =====
pause
exit /b 1
