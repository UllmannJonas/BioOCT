@echo off
REM ------------------------------------
REM Start Napari Script
REM ------------------------------------

REM Path
set SCRIPT_DIR=%~dp0

REM Path to venv
set VENV_PATH=%SCRIPT_DIR%.venv

REM activate venv
call "%VENV_PATH%\Scripts\activate"

REM start napari
napari
pause
