@echo off
setlocal

set "BIOOCT_DIR=%USERPROFILE%\BioOCT"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo ============================================
echo  BioOCT - Setup and Start
echo ============================================
echo.
echo This window will take care of everything needed
echo to run BioOCT. The first run can take a few minutes,
echo every run after that will be quick.
echo.

if not exist "%BIOOCT_DIR%" mkdir "%BIOOCT_DIR%"
cd /d "%BIOOCT_DIR%"

where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv ^(a Python package manager, only needed once^)...
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo.
        echo Could not install uv. Please check your internet connection
        echo and try running this file again.
        pause
        exit /b 1
    )
)

echo.
echo Preparing the Python environment...
REM uv will auto install python if not found on system (https://docs.astral.sh/uv/guides/install-python/#viewing-python-installations)
uv venv --python 3.12
if errorlevel 1 (
    echo.
    echo Something went wrong while preparing the environment.
    echo If the message above mentions "os error 5" or "failed to rename file",
    echo this is a known issue caused by antivirus software interfering with uv:
    echo https://github.com/astral-sh/uv/issues/16747
    echo Try temporarily disabling real-time protection and run this file again.
    pause
    exit /b 1
)

echo.
echo Installing/updating BioOCT and its requirements...
uv pip install napari bio-oct napari-nifti pyqt6
if errorlevel 1 (
    echo.
    echo Installation failed. Please copy the error message above
    echo and report it here:
    echo https://gitlab.kit.edu/kit/ebi/dvgw/watertechnology/bio-oct/-/issues
    echo OR
    echo https://github.com/UllmannJonas/BioOCT/issues
    pause
    exit /b 1
)

echo.
echo Starting BioOCT...
".venv\Scripts\python.exe" -m napari

pause
