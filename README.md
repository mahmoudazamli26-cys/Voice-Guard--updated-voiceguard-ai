# VoiceGuardAI

An educational voice deepfake research application with an English/Arabic interface, bounded in-memory audio analysis, overlapping-window scores, spectrograms, optional occlusion analysis and model comparison. **A detector cannot prove authenticity or fraud.** The interface shows the higher-scoring real/fake class as a model prediction. Silent, tied or disagreeing results remain inconclusive. In calibrated mode the interface respects the fitted abstention region; reports retain the raw model prediction separately.

## Run

Python 3.12 and FFmpeg are required. Install FFmpeg through your OS package manager (`sudo apt-get install ffmpeg` on Debian/Ubuntu), then:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
```

On Windows, create the environment with `py -3.12 -m venv .venv` and activate using `.venv\Scripts\activate`. Ensure `ffmpeg` is on PATH. `python app.py` does not start an ASGI server.

The frontend and API share port 8000. Model initialization runs in the application lifespan; `/health` reports readiness (503 if loading failed). The first start downloads the pinned public model; subsequent starts reuse Hugging Face's cache. Set `HF_HOME` to a writable persistent cache if needed. Keep one worker: the rate/concurrency limits are process-local. For remote use, see [SECURITY.md](SECURITY.md).

### Experimental Arabic profile

An optional small trained classifier reuses the same encoder and frontend. On a fresh 256-clip public ArAD subset, matched accuracy improved from **54.69% to 71.88%**, with better fake recall and digital robustness. These are exploratory clip-level results; new-speaker generalization is unverified. The general profile remains the default.

On an existing Windows installation, stop the old backend and double-click `start_arabic.bat`. See [step-by-step launch instructions](docs/ARABIC_PROFILE.md) and [full evidence and limitations](docs/results/model-improvement/README.md). Other shells can set `VG_PROFILE=experimental-arabic` before starting uvicorn. No extra runtime dependencies are required.

Alternatively, with Docker:

```bash
docker compose up --build
```

Compose uses a non-root, resource-limited container, one local port and a persistent model cache. First start requires model download access; `/health` must become ready before analysis. A proxy-constrained cloud builder may require its existing proxy host mapping, build proxy arguments and trusted CA; do not disable TLS/signature verification. See the implementation status for the validation performed here.

## Use

1. Confirm permission and processing consent; choose, drag/drop or record audio.
2. The browser checks size and duration. The server independently enforces limits, decodes the actual audio container and bounds concurrency and request rate. A bundled speech detector checks for at least 250 ms of consecutive speech first. When no speech is detected, the page asks you to record someone speaking; the classifier is not run and no real/fake percentage is returned.
3. Analyze: 5-second windows with a 2.5-second stride, including the tail, produce a timeline and aggregate score (`mean` by default; `max` is configurable). Short recordings use one window.
4. Optional occlusion (up to 30 seconds) replaces each interval with silence and recomputes all affected overlapping windows. Its score change is shown in the table. The spectrogram is a signal visualization, not proof of explainability or manipulation.
5. Download a JSON report with SHA-256 of the original uploaded bytes, model identities, scores, windows, disclaimer and timestamp. Reports keep the separate `model_prediction` (raw higher-scoring class) and `prediction` (calibration/abstention decision) fields. The app does not retain uploads or reports. Treat hashes as potentially sensitive metadata.

Supported containers: WAV, MP3, FLAC, OGG, M4A, WebM. Defaults: 15 MiB, 120 seconds, six analysis requests/minute per direct peer, one inference at a time. Speech detection is imperfect: quiet or heavily distorted speech may be missed, and some non-speech sounds may resemble speech. Retry with clear speech if needed. This API gate is separate from the raw classifier used by research CLI workflows.

Microphone recording needs a secure browser context (HTTPS or local development) and permission.

### API

- `GET /health`: model readiness and public limits.
- `POST /api/v1/analyze?explain=false`: multipart fields `file` and `consent=true`; typed JSON result. `/analyze` is an alias.
- `GET /openapi.json`: API schema. Interactive CDN-based API docs are disabled to preserve a same-origin CSP.

```bash
curl -f -F consent=true -F file=@sampleA_short.wav http://127.0.0.1:8000/api/v1/analyze
```

The bundled recordings are **unlabeled**. This command is a functional check, not an accuracy benchmark.

## Calibration, evaluation and Arabic research

See [the protocol and commands](docs/RESEARCH.md) and [manifest instructions](data/README.md). `evaluate.py` computes accuracy, precision/recall, F1, a confusion matrix, ROC and interpolated EER; it writes JSON and a PNG chart. Calibration is allowed on validation data only (at least 20 real and 20 fake examples), with separate low/high thresholds and an abstention region. No arbitrary 40/70 risk bands remain.

`robustness.py` compares paired MP3 compression, 10/20 dB noise and 8 kHz resampling, and accepts actual loudspeaker re-recordings. `train_arabic.py` optionally fine-tunes on consented Arabic training speakers, selecting by validation loss. The scripts reject missing consent, duplicate content and cross-split speakers.

No labeled dataset was supplied by the user. Small public ArAD classifier and digital robustness measurements are available in [the exploratory results](docs/results/README.md), with their limits. **A consented, speaker-independent Arabic study and final production thresholds remain pending.** Experimental public-clip calibration is now fitted and tested: [thresholds and coverage](docs/CALIBRATION.md). Start it on Windows with `start_calibrated_arabic.bat`. It decided 32/256 fresh clips, with 29 correct and 224 inconclusive; this is not 90.6% accuracy across all clips. The [eight-clip physical test guide](docs/PHYSICAL_TEST.md) provides prepare/evaluate launchers; the initial eight-pair user-run physical pilot is now complete and exposed a substantial false-real weakness. See [robustness improvement work](docs/ROBUSTNESS_IMPROVEMENT.md). Public clip-level results cannot establish performance on new speakers or all Arabic dialects. Do not publish software-test fixture metrics as research findings.

### Optional second model

A compatible second model is loaded only when configured. This pair was exercised on a bundled sample; disagreement correctly abstained:

```bash
export VG_SECOND_MODEL=mo-thecreator/Deepfake-audio-detection
export VG_SECOND_REVISION=e4d9874b493362149cec96ced85f00b00b1a04c0
# Restart the server, then evaluate/calibrate this exact ensemble independently.
```

Both individual model scores are included in the downloadable JSON report. Recheck model cards/licenses for your intended use. The models can share training biases; an ensemble is not a guaranteed improvement.

## Configuration

Variables in `.env.example` are references; the server reads the process environment and does not implicitly load `.env` files. `VG_MODEL_ID`, `VG_MODEL_REVISION`, `VG_SECOND_MODEL`, `VG_SECOND_REVISION`, `VG_CALIBRATION`, `VG_MAX_BYTES`, `VG_MAX_SECONDS`, `VG_RATE_LIMIT`, `VG_AGGREGATION`, `VG_CPU_THREADS` and `VG_INFERENCE_BATCH_SIZE` configure inference. `VG_PROFILE` selects `base`, `experimental-arabic` or `experimental-arabic-calibrated`; `VG_HEAD_PATH` optionally provides a matching JSON classifier. Normal inference batches up to three equal-length windows and caps CPU threads at four by default (an existing `OMP_NUM_THREADS` setting is respected). Use `VG_INFERENCE_BATCH_SIZE=1` for the serial path or lower peak memory. Keep the explanation checkbox off for the fastest normal analysis; it requires extra masked inference. A second model also adds inference work. Public models need no API key. A calibration must match both model revisions, any adapted head checksum, and windowing/aggregation; local model artifacts are hashed as part of calibration identity. JSON reports identify adapted classifiers with `models[].head_sha256`.

## Validation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m bandit -r app.py voiceguard evaluate.py robustness.py train_arabic.py public_arabic_benchmark.py compare_arabic_models.py train_public_head.py -ll
python -m pip_audit --progress-spinner off
# Also audit the upstream torch version: local +cpu variants are not listed on PyPI.
python -m pip_audit -r requirements.txt --disable-pip --no-deps --progress-spinner off
```

The suite includes API abuse cases, no-disk-spooling assertions, window/ensemble/calibration behavior, metric checks and end-to-end research CLI tests using a tiny random model and synthetic tones. These fixtures test software, not detection quality. Bandit reports low-severity warnings for fixed-argument FFmpeg subprocesses; medium/high findings fail CI.

For browser validation, start the real server, then:

```bash
npm ci
npx playwright install chromium
npm run test:browser
# Or use a system browser: VG_BROWSER_PATH=/usr/bin/chromium npm run test:browser
```

This checks real uploads, reports, mobile RTL layout, microphone recording using a fake browser audio device, drag/drop and English/Arabic axe accessibility rules. Screenshots are stored under ignored `reports/browser/`. GitHub Actions runs Python tests, dependency/Bandit scans and a Docker build; Dependabot monitors Python, actions and Docker.

See [the PDF implementation checklist and validation record](docs/IMPLEMENTATION_STATUS.md), [STRIDE threat model](docs/THREAT_MODEL.md) and [security limitations](SECURITY.md).

## Attribution and license

Base model: [garystafford/wav2vec2-deepfake-voice-detector](https://huggingface.co/garystafford/wav2vec2-deepfake-voice-detector), pinned at `c66306024a7ede0be291e9c4558b37634782dc4e`. Optional comparison model: [mo-thecreator/Deepfake-audio-detection](https://huggingface.co/mo-thecreator/Deepfake-audio-detection). Models and datasets retain their own licenses and usage conditions. The locally served DejaVu font's license is in `frontend/FONT-LICENSE.txt`. The original Reaper AI header, hero, footer, PNG logo and base stylesheet are preserved from `frontend.zip`. New analysis controls use `frontend/enhancements.css` inside the middle panels. The archive itself is not served.

Project code is MIT-licensed; see [LICENSE](LICENSE). Developed as an educational student project by Reaper Team.

Speech detection uses the bundled Silero VAD TorchScript model from the official `silero-vad` 6.2.3 PyPI wheel. The wheel SHA-256 was verified before extracting the model; model provenance and the MIT license are in `voiceguard/assets/`. The model checksum is checked before loading. It reuses installed PyTorch and requires no extra runtime download or new package.

The original logo is served as pixel-identical lossless WebP (40.4% smaller than its PNG source). DejaVu Sans is explicitly loaded locally as preloaded WOFF2 (66.0% smaller than the TTF source), with Arabic mappings retained and `font-display: swap`. Its license is bundled. Source PNG/TTF files remain for reference; the current page requests only the optimized assets. Font and image conversions require no new runtime packages.
