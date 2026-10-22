@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Use your existing project folder containing .venv.
    pause
    exit /b 1
)
echo This processes your phone files locally. It does not upload them.
set "VG_PHYSICAL_FOLDER=%LOCALAPPDATA%\VoiceGuardAI\physical-test"
choice /c YN /n /m "Were these captured through a REAL speaker and microphone, with permission and no bystanders? [Y/N] "
if errorlevel 2 exit /b 1
set "VG_PROFILE=experimental-arabic-calibrated"
set "VG_HEAD_PATH="
set "VG_MODEL_ID=garystafford/wav2vec2-deepfake-voice-detector"
set "VG_MODEL_REVISION=c66306024a7ede0be291e9c4558b37634782dc4e"
set "VG_SECOND_MODEL="
set "VG_SECOND_REVISION="
set "VG_CALIBRATION="
set "VG_AGGREGATION=mean"
".venv\Scripts\python.exe" physical_loudspeaker_test.py evaluate --folder "%VG_PHYSICAL_FOLDER%" --confirm-recording-permission --confirm-physical-capture
if errorlevel 1 (
    pause
    exit /b 1
)
start "" "%VG_PHYSICAL_FOLDER%"
pause
