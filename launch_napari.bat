@echo off
REM -----------------------------
REM Start Napari with OCT plugin
REM -----------------------------

REM Pfad zur virtuellen Umgebung
set VENV_PATH=C:\Users\sx1218\Arbeitsordner\Python\oct-analysis\.venv

REM Aktivieren der venv
call "%VENV_PATH%\Scripts\activate.bat"

REM Napari starten
napari
