@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Use your existing project folder containing .venv.
    pause
    exit /b 1
)
set "VG_PHYSICAL_FOLDER=%LOCALAPPDATA%\VoiceGuardAI\physical-test"
".venv\Scripts\python.exe" physical_loudspeaker_test.py prepare --folder "%VG_PHYSICAL_FOLDER%"
if errorlevel 1 (
    echo Preparation failed. Check your connection and try again.
    pause
    exit /b 1
)
start "" "%VG_PHYSICAL_FOLDER%\play_samples.html"
start "" "%VG_PHYSICAL_FOLDER%\recordings"
echo Record each sample with your phone, then copy the files into the recordings folder just opened.
pause
