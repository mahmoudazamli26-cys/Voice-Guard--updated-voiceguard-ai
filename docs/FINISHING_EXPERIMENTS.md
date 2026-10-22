# Remaining experiments

## Public Arabic exploration

`public_arabic_benchmark.py` downloads the pinned **publisher test partition**
of [ArAD, DeepFake-Audio-Rangers](https://huggingface.co/datasets/DeepFake-Audio-Rangers/Arabic_Audio_Deepfake).
The dataset card declares ODC-By-1.0 and describes mostly Levantine Arabic,
RVC-generated fakes and cleaned clips of at most about three seconds. Credit
the dataset publisher when sharing results and consult the linked license.

This is a separate exploratory workflow. The card provides neither speaker IDs
nor individual consent records. It cannot establish speaker-disjoint performance,
permission to clone speakers, or absence of overlap with detector training data.
The script does not invent speaker IDs, mark consent as true, train, calibrate,
or change the application's decision thresholds. Do not present these results as
the completed consented study in `RESEARCH.md`.

```sh
python -m pip install -r requirements-research.txt
python public_arabic_benchmark.py
```

Default selection is 64 examples per class, sampled with a fixed seed after
exact-byte deduplication. The 32-example balanced robustness subset is selected
before inference. Every sample's row index, audio checksum, label and score is
recorded. The downloaded source revision and checksum, pinned model identity,
ROC, confusion matrix, accuracy, precision/recall/F1, AUC, EER and paired digital
robustness measurements are saved. Speech-gate rejection counts are separate
from classifier metrics. Small sample uncertainty and unverified speaker overlap
must remain visible whenever reporting the numbers.

## Consented calibration and optional fine-tuning

Use `data/README.md` and `data/example.csv` for your own recordings. Keep every
speaker and their synthetic versions in one split. Keep consent evidence private.
Reserve test speakers before fitting thresholds. At least 20 real and 20 fake
validation examples are required by the software; more speakers and recordings
are needed to make dependable claims. Follow `RESEARCH.md` for the commands.

Do not turn this public test subset into training or validation data just to
produce an apparent improvement. Fine-tuning is optional in the PDF; report it
as unrun until a suitable training/validation/test collection exists.

## Physical loudspeaker experiment

1. Start with recordings you have permission to play and re-record. Assign each
   original a unique `pair_id` in its manifest.
2. Play each clip through a real loudspeaker. Record it with another device,
   without changing the real/fake ground-truth label. Document distance, device,
   room and volume. Do not include bystanders' voices.
3. Save the recordings privately. Create a second manifest with matching
   `pair_id`, `speaker`, `language`, `label`, `split` and documented consent.
4. Run `python robustness.py data/manifest.csv --split test --language ar
   --rerecorded data/rerecorded.csv --output reports/loudspeaker.json` on one line.
5. Report the paired score changes and detection metrics. Digital compression or
   added noise does not count as completing this physical experiment.

## Your silent microphone example

The included no-speech tests do not reproduce every microphone environment.
Restart the latest backend and refresh the browser before checking again. If a
silent recording still receives a real/fake score, retain that exact clip and its
JSON report for investigation. The report's `speech_detected` and
`decision_reason` fields distinguish speech-gate acceptance from an old backend.
Do not tune the detector solely to a screenshot or label background noise as real.
