# Consented recordings

Copy `example.csv` and add **real recordings**, not placeholder rows. Required columns:
`path,label,speaker,language,split,consent`. Optional `pair_id` associates an original with a physical loudspeaker re-recording in a second manifest.

- `path`: relative to the CSV; `label`: `real` or `fake`; `language`: e.g. `ar` or `en`.
- `speaker`: stable, pseudonymous identity grouping both the real voice and its clones. Keep every speaker entirely in ONE split (`train`, `validation`, `test`). Keep shared source utterances, generator runs, and near duplicates in one split as well.
- `consent`: `true` only with permission for the specific recording, synthetic reproduction, and intended use. Store the consent record privately, outside Git. Do not publish private audio or identifiable speaker metadata.
- Include multiple speakers, Arabic dialects, genders, generators, durations, and recording devices. Report counts and known sampling biases. An Arabic subset needs both classes.
- Calibration requires at least 20 real + 20 fake **validation** examples. This is a floor for a demonstration, not adequate proof of generalization. Reserve test speakers before selecting models or thresholds.
- For Arabic TTS, verify current model language support, license, voice-cloning restrictions, and consent before generation. XTTS is a candidate, not a bundled or verified dependency. Do not clone an unconsenting person.
- Do not use the included unlabeled sample audio as ground truth or claim Arabic results without data.

Loudspeaker testing is a physical experiment: play the original through a speaker, record with another microphone, retain the same label/speaker/language and unique `pair_id`, and evaluate with `robustness.py --rerecorded rerecorded.csv`. Digital noise does not substitute for this test.
