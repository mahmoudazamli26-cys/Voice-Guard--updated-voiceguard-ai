@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Your Python environment was not found in this folder.
    echo Copy the updated project files into your existing project folder, keeping .venv.
    echo See docs\ARABIC_PROFILE.md for setup instructions.
    pause
    exit /b 1
)
if not exist "voiceguard\assets\arabic_head.json" (
    echo The Arabic classifier file is missing. Extract the complete updated project.
    pause
    exit /b 1
)
set "VG_PROFILE=experimental-arabic"
set "VG_HEAD_PATH="
set "VG_MODEL_ID=garystafford/wav2vec2-deepfake-voice-detector"
set "VG_MODEL_REVISION=c66306024a7ede0be291e9c4558b37634782dc4e"
set "VG_SECOND_MODEL="
set "VG_SECOND_REVISION="
set "VG_CALIBRATION="
echo Starting the experimental Arabic classifier.
echo Stop any previous VoiceGuard server with Ctrl+C first.
echo After Application startup complete, open http://127.0.0.1:8000
echo Public ArAD clip-level testing does not establish performance on new speakers.
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
pause
