# Improving speaker/phone robustness

The user's eight physical pairs exposed a real limitation, not an error to hide
by choosing new thresholds on those same recordings. Keep those recordings as
reviewed test evidence. They must not enter training or calibration. Further
physical confirmation needs fresh recordings because this failure has already
influenced the improvement approach.

## Current physical pilot

Four publisher-labeled real and four fake originals were played through the
user's laptop speaker and captured with a phone. Capture and new-recording
permission are user-attested. Source speaker identities and consent remain
unknown. The report contains no room/device measurements. These are eight pairs,
not a claim about other phones, rooms or speakers.

At the diagnostic raw 0.5 cutoff, accuracy changed from 7/8 (87.5%) to 4/8
(50%); fake recall changed from 3/4 to 0/4. Experimental calibration made one
correct fake decision on originals with seven inconclusive. On phone recordings
it called six real (three correct, three incorrect) and left two inconclusive.
All eight were speech-detected. Mean fake-class score fell by 22.42 percentage
points. The published clean-clip calibration does not establish phone robustness.

The user supplied the JSON report for review. Private phone hashes and the full
report are not automatically published to the repository; no phone audio is
included. These aggregate counts describe the supplied report, not independent
authentication of physical capture or source labels.

## Reproducible candidate experiment

`voiceguard/channel.py` creates label-independent randomized bandwidth limits,
early echoes, impulse decay, background noise and gain. Different clip/split seeds
prevent reuse of an identical synthetic channel across partitions. These are
simple synthetic stressors, not measured room impulse responses or actual phone
captures. There is no assertion that they replicate the user's Samsung/laptop
path or that synthetic gains will transfer to it.

`train_channel_head.py` keeps the pretrained encoder/projector fixed and fits
one classifier using original plus mild/strong simulated versions of the existing
256 public training clips (768 feature vectors). It uses the existing 64
development clips, excluding the previous calibration and test sources. It
reserves 128 fresh publisher-test clips, excluding every previously reviewed
test and the original physical-source clips, before scoring. Exact-byte
disjointness does not establish speaker or utterance independence.

The fixed regularization is C=0.1. The predeclared development rule requires at
least five percentage points of improvement for each simulated channel and no
more than three points lost on clean audio. Confirmation uses the same rule and
requires fake recall not to fall for either simulated channel. Failed development
keeps confirmation unopened. Reports distinguish all conditions and models; raw
classifier diagnostics precede speech gating and do not use old calibration with
new weights. The candidate is never automatically installed in the app.

```sh
python -m pip install -r requirements-research.txt
python train_channel_head.py --stage prepare
python train_channel_head.py --stage fit
# Only after development passes:
python train_channel_head.py --stage confirmation
```

## Before a robustness claim or deployment

Gather separate labeled, permissioned physical training and validation recordings
using multiple rooms, speaker/microphone devices and distances. Split by source
speaker/utterance before augmentation or capture; paired original/capture audio
must stay in one partition. Fit or select on training/development, then fit
abstention thresholds on validation only. Bind new calibration to the new head
checksum. The previous clean-head thresholds cannot be reused.

Freeze the model and thresholds, then test fresh physical clips. Report fake
recall, false-real errors, real/fake decisions, coverage and inconclusive counts,
not accuracy alone. If these checks fail, the model remains experimental; changing
colors or lowering a cutoff does not fix its discrimination. Simulation results
alone do not complete physical robustness validation.
