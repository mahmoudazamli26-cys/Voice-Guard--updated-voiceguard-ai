# Start the experimental Arabic profile

The profile replaces only the final classifier of the existing pinned model.
It uses the same encoder, frontend and no-speech guard. It needs no new runtime
packages or second full model download if the original pinned model is cached.
The small trained classifier is bundled in `voiceguard/assets/arabic_head.json`.

## Windows, using your existing installation

1. Download the latest ZIP from the `updated-voiceguard-ai` GitHub branch and
   extract it. Copy the updated project files into your existing project folder,
   allowing file replacement. Keep your existing `.venv` folder there.
2. In the terminal running the old backend, press **Ctrl+C** to stop it.
3. In the project folder, double-click **start_arabic.bat**. Keep its window open.
4. Wait for **Application startup complete**, then open **http://127.0.0.1:8000**.
5. Refresh with **Ctrl+F5**, choose or record Arabic speech, confirm permission,
   and analyze. Leave muting analysis unchecked for the fastest normal result.

The launcher prints the selected profile. Downloaded JSON reports include
`models[0].head_sha256`, identifying the trained head. Changing the page's
Arabic/English display language alone does not change the backend model.

If you extracted into a brand-new folder without `.venv`, follow the Windows
Python/FFmpeg and dependency instructions in the root README first. Do not copy
only the frontend: this update includes backend code and the trained classifier.

To use the original profile again, stop this server and start your normal
uvicorn command in a fresh terminal. The launcher uses `setlocal`, so its
environment changes do not persist outside its window.

## Command Prompt alternative

From your project folder with `.venv` activated:

```bat
set VG_PROFILE=experimental-arabic
set VG_CALIBRATION=
set VG_SECOND_MODEL=
set VG_SECOND_REVISION=
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
```

The default general profile remains `base`. Advanced operators can provide a
matching numeric head with `VG_HEAD_PATH`; different models, label maps, dimensions
or old calibration identities are rejected.

## What improved, and what remains unknown

On a fresh balanced **256-clip public ArAD subset**, the old classifier achieved
**54.69%** accuracy and the adapted one **71.88%**, at the same diagnostic 0.5
cutoff. Fake recall improved from **36.72% to 61.72%**. These are matched-clip
measurements, not a comparison with the earlier separate 128-clip result.

The adapted head also passed predefined development and digital robustness
checks. See [the complete evidence](results/model-improvement/README.md).
The classifier still missed 49 of 128 labeled fakes in confirmation. The public
dataset lacks speaker IDs and individual consent records, covers mainly
Levantine/RVC clips, and cannot establish generalization to new speakers,
dialects, generators, devices or long recordings. This is an **experimental
profile**, not a validated Arabic authenticity test. Its class scores are not
probabilities of fraud. No production abstention thresholds were fitted.

The dataset remains credited to ArAD / DeepFake-Audio-Rangers under its stated
ODC-By-1.0 license. No source audio or extracted voice features are redistributed.

## Optional fitted abstention

The separate `start_calibrated_arabic.bat` launcher uses the same head with
validation-fitted experimental thresholds. It decided only 32 of 256 fresh test
clips (12.5% coverage); the rest were inconclusive. See [calibration evidence and
limitations](CALIBRATION.md). The existing raw launcher remains available.
