@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Use your existing project folder containing .venv.
    pause
    exit /b 1
)
if not exist "voiceguard\assets\arabic_calibration.json" (
    echo The calibration file is missing. Copy the complete updated voiceguard folder.
    pause
    exit /b 1
)
set "VG_PROFILE=experimental-arabic-calibrated"
set "VG_HEAD_PATH="
set "VG_MODEL_ID=garystafford/wav2vec2-deepfake-voice-detector"
set "VG_MODEL_REVISION=c66306024a7ede0be291e9c4558b37634782dc4e"
set "VG_SECOND_MODEL="
set "VG_SECOND_REVISION="
set "VG_CALIBRATION="
set "VG_AGGREGATION=mean"
echo Starting experimental calibrated Arabic mode.
echo Stop the previous server with Ctrl+C first.
echo Most test clips were inconclusive; this mode does not prove authenticity.
echo After Application startup complete, open http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
pause
