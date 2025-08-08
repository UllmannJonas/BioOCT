@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m napari
) else (
    echo Virtuelle Umgebung nicht gefunden!.
    pause
)
pause