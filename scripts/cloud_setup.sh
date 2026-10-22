#!/usr/bin/env bash
set -euo pipefail
cd /workspace/Voice-Guard-
python -m venv /workspace/voiceguard-env
export PIP_CACHE_DIR=/workspace/voiceguard-cache/pip
export HF_HOME=/workspace/voiceguard-cache/huggingface
export NUMBA_CACHE_DIR=/workspace/voiceguard-cache/numba
export PYTHONPYCACHEPREFIX=/workspace/voiceguard-cache/pycache
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p "$PIP_CACHE_DIR" "$HF_HOME" "$NUMBA_CACHE_DIR"
/workspace/voiceguard-env/bin/python -m pip install --upgrade pip setuptools
/workspace/voiceguard-env/bin/python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
/workspace/voiceguard-env/bin/python -m pip install -r requirements-dev.txt
/workspace/voiceguard-env/bin/python -m pip check
command -v ffmpeg >/dev/null
/workspace/voiceguard-env/bin/python - <<'PY'
from huggingface_hub import snapshot_download
for model, revision in [
    ('garystafford/wav2vec2-deepfake-voice-detector', 'c66306024a7ede0be291e9c4558b37634782dc4e'),
    ('mo-thecreator/Deepfake-audio-detection', 'e4d9874b493362149cec96ced85f00b00b1a04c0'),
]:
    snapshot_download(model, revision=revision, allow_patterns=['*.json', '*.safetensors'])
PY
/workspace/voiceguard-env/bin/python -m pytest -q
