# Reproducible research protocol

Question: **How reliable are open deepfake voice detectors on Arabic speech, compression, noise, and physical re-recordings?**

1. Obtain consented data and complete `data/example.csv`; see `data/README.md`. Record generator/license/collection details privately. Split by speaker and source before model selection. Never label the bundled unlabeled samples by guessing.
2. Freeze the base model/revision and report real/fake counts, speakers, dialects and generators in each split. Use independent test data; do not train and test on overlapping speakers or utterances.
3. Run validation once for threshold selection. `evaluate.py` reports accuracy, precision, recall, F1, confusion matrix (rows true, columns predicted), ROC AUC and linearly interpolated EER. Fake is positive. The fixed 0.5 decision is diagnostic, not the application's production threshold.
4. Calibrate two abstention thresholds on validation only, requiring at least 20 examples per class. The script maximizes validation coverage among candidates that constrain empirical class-conditional false-real/false-fake rates. This is not a confidence guarantee; include uncertainty and larger data before deployment.
5. Evaluate the frozen configuration on held-out test speakers. Report abstention coverage, false-real/false-fake rates and accuracy on decided cases separately. `real` means below a model threshold, not proven authentic. Report each language independently.
6. Test paired MP3 32 kbps, Gaussian noise at 20/10 dB SNR, and 8 kHz channel resampling. Physical speaker/microphone re-recordings require actual new recordings and matching `pair_id`; simulated noise is not a substitute.
7. Optionally compare a second two-label safetensors audio classifier. Set `VG_SECOND_MODEL` and immutable `VG_SECOND_REVISION`. Explicit real/bonafide and fake/spoof labels are required; ambiguous LABEL_0/LABEL_1 mappings are rejected. Evaluate/calibrate the ensemble separately. Mean model scores are combined per window. Opposite-side diagnostic scores or differing calibrated decisions cause abstention.
8. Optional Arabic fine-tuning: train on Arabic training speakers only. The feature encoder is frozen; the remaining model is optimized on random 5-second crops. Pick the checkpoint by validation loss, never test loss. Run the same full-recording test evaluation before and after, each with its own validation calibration. Record hyperparameters and counts in `training.json`.

```bash
python evaluate.py data/manifest.csv --split validation --calibrate models/base-calibration.json --output reports/base-validation.json
VG_CALIBRATION=models/base-calibration.json python evaluate.py data/manifest.csv --split test --output reports/base-test.json
VG_CALIBRATION=models/base-calibration.json python evaluate.py data/manifest.csv --split test --language ar --output reports/base-arabic.json
python robustness.py data/manifest.csv --split test --language ar
# Requires physical re-recordings:
python robustness.py data/manifest.csv --rerecorded data/rerecorded.csv
# Optional, resource-intensive; run only once suitable consented data exists:
python train_arabic.py data/manifest.csv --output models/arabic --epochs 3 --batch-size 2
VG_MODEL_ID="$PWD/models/arabic" VG_MODEL_REVISION=local python evaluate.py data/manifest.csv --split validation --calibrate models/arabic-calibration.json --output reports/arabic-validation.json
VG_MODEL_ID="$PWD/models/arabic" VG_MODEL_REVISION=local VG_CALIBRATION=models/arabic-calibration.json python evaluate.py data/manifest.csv --split test --output reports/arabic-test.json
```

The first model/revision is pinned in `voiceguard/config.py`. For a locally fine-tuned checkpoint, archive its files and training manifest hashes alongside the report; The calibration identity includes a SHA-256 digest of local JSON and safetensors artifacts; a modified local checkpoint is rejected until recalibrated. Do not compare calibration from one model to another.

**Honest reporting:** no labeled dataset was supplied by the user during implementation. Public ArAD inference and a separate frozen-encoder head adaptation are documented in `results/README.md` and `results/model-improvement/README.md`; these do not meet this protocol's consent and speaker-disjoint requirements. Head-only adaptation improved matched fresh-clip accuracy from 54.69% to 71.88%; this is not a full encoder fine-tuning result or proof of new-speaker performance. No completed consented Arabic study, physical re-recording result or ensemble superiority has been established. Unit-test fixtures exercise software behavior and are never research evidence. The included audio supports a functional smoke test only. A UI spectrogram alone is not explainability; the optional occlusion computation actually reruns masked overlapping windows and reports the score delta, with off-manifold masking limitations.

## Experimental public calibration update

A separate public-clip study has now fitted thresholds on 128 reserved validation
clips and tested a frozen configuration on 256 fresh clips. It does not satisfy
the consented speaker-disjoint protocol above. See [complete results and
coverage](CALIBRATION.md) and [actual physical-capture instructions](PHYSICAL_TEST.md).
The physical kit is prepared; no phone capture or physical result is claimed yet.
