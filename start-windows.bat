@echo off
title ModFerry
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 (echo Python 3.11+ is required: https://www.python.org/downloads/ & pause & exit /b 1)
)
.venv\Scripts\python.exe -c "import sys; sys.exit(sys.version_info < (3, 11))"
if errorlevel 1 (echo The .venv folder uses an older Python. Install Python 3.11+, delete the .venv folder and start again. & pause & exit /b 1)
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (echo Installation failed. & pause & exit /b 1)
if "%MODFERRY_PORT%"=="" set MODFERRY_PORT=8765
start "" "http://127.0.0.1:%MODFERRY_PORT%"
.venv\Scripts\python.exe app.py
pause
