# Experimental Arabic calibration

Fitted thresholds now exist for the frozen public Arabic head. This is
**experimental clip-level calibration**, not final validated production
thresholds or a completed consented speaker-independent study.

## Use it on Windows

Update your project files while keeping `.venv`, stop the old backend with
**Ctrl+C**, and double-click **start_calibrated_arabic.bat**. Wait for startup,
open http://127.0.0.1:8000 and refresh with **Ctrl+F5**.

The existing `start_arabic.bat` still starts raw experimental class predictions.
The new launcher starts the same trained head with validation-fitted abstention.
The layout and fake-red / real-green / inconclusive-orange colors are preserved.

For other shells, set `VG_PROFILE=experimental-arabic-calibrated` and start the
usual uvicorn command. This profile selects the bundled head and matching
`voiceguard/assets/arabic_calibration.json`. Explicit `VG_CALIBRATION` overrides
the path; an explicitly empty value disables calibration in shells supporting
empty variables. Model/head/window/aggregation mismatches fail readiness.

## Thresholds and evidence

- **Real decision:** fake-class score at or below **27.700889%**.
- **Fake decision:** fake-class score at or above **74.284089%**.
- **Inconclusive:** between those thresholds, model disagreement, or no speech.

The full-precision values in the bundled JSON drive decisions; these percentages
are explanatory, not fraud probabilities. No-speech checks still run first.

The head and thresholds were frozen separately. A new balanced 128-clip subset
of the publisher training partition fitted thresholds, excluding head-training
and development clips and all publisher test byte hashes. Only detected-speech
validation clips entered fitting. A predefined empirical class-error target of
2% was used; it is not a confidence guarantee. No threshold was fitted to test
scores or physical recordings.

A fresh balanced **256-clip test** excluded every previously reviewed test clip:

| Measurement | Result |
|---|---:|
| Raw classifier accuracy at 0.5, before speech gating | 72.27% |
| Calibrated real/fake decisions | 32 / 256 (12.5% coverage) |
| Inconclusive | 224 / 256 (87.5%) |
| Correct among the 32 decisions | 29 / 32 (90.625%) |
| Fake clips called real | 3 / 128 (2.34375%) |
| Real clips called fake | 0 / 128 |

**90.625% applies only to the 32 decided cases. It is not accuracy across all
256 clips.** Inconclusive cases are not counted as correct. Of 21 green real
decisions, three were wrong; a green result still does not prove authenticity.
The predeclared test check required at least 10% coverage and at most 5% observed
false-real and false-fake rates per true class; it passed on this small subset.
These empirical rates do not guarantee future rates.

Digital robustness was also rerun on 16 paired clips. The strict thresholds
abstained on all original/resampled clips in that subset and all but one or two
noisy/compressed clips. This demonstrates limited coverage, not proven robustness
or perfect accuracy. Physical loudspeaker results remain pending actual capture.

The UI now respects calibrated decisions and model-disagreement abstention,
instead of replacing them with the larger raw class. Reports retain raw
`model_prediction` separately from backend `prediction` and calibration metadata.

## Reproduction and limits

```sh
python -m pip install -r requirements-research.txt
python calibrate_public_arabic.py --stage prepare
python calibrate_public_arabic.py --stage calibrate
python calibrate_public_arabic.py --stage test
```

Protocols, source checksums, frozen clip selections, validation/test scores and
decisions are in [the evidence](results/calibration/). Source audio is not
redistributed. This uses the pinned ArAD release credited to
DeepFake-Audio-Rangers under its stated ODC-By-1.0 license. Publisher labels are
unverified; speaker IDs, individual consent and utterance independence are
unknown. Near duplicates or pretrained-data overlap cannot be ruled out. The
corpus mainly covers short Levantine/RVC clips. Proper consented, speaker-disjoint
validation on the intended deployment population remains required for a claim
of final general-purpose thresholds.
