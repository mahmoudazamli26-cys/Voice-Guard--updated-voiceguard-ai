# Arabic model improvement protocol

The existing 128-clip ArAD result is already reviewed. It is not used for
threshold fitting, model selection, or a new claim of confirmation performance.
There is no consented speaker-disjoint corpus available for fine-tuning.

The comparison in `compare_arabic_models.py` tests one predefined candidate:
[Gustking's XLS-R detector](https://huggingface.co/Gustking/wav2vec2-large-xlsr-deepfake-audio-classification),
revision `f7050b586236dc910d1157f430def2d0647b02b4`, stated Apache-2.0 license.
Its multilingual encoder is a reason to investigate it, not evidence of better
Arabic detection. The baseline remains the pinned garystafford model.

The dataset is the same pinned, publicly licensed ArAD release credited in
`results/README.md`. This workflow only performs inference; it does not clone
voices, fine-tune weights, assert individual consent, or fit thresholds.

1. Development: select 32 real and 32 fake clips from all three publisher training
   shards. Exclude exact byte matches with **the entire publisher test split**.
2. Save the protocol and clip checksums before model loading. Use the fixed
   diagnostic threshold 0.5. Require at least five percentage points of accuracy
   gain, five points of fake-recall gain, and at most two points of real-recall loss.
3. Only if development passes, score a frozen fresh balanced 256-clip subset
   from the publisher test partition, excluding the previously reviewed 128 clips.
4. Repeat the accuracy/recall criteria on confirmation. On a predefined balanced
   16-clip robustness subset, also require that no tested compression, noise or
   resampling condition loses accuracy versus the old model on those same clips.
5. Report all results, including failed criteria. Keep raw classifier metrics
   separate from speech gating and calibrated abstention. A failed candidate
   must not replace the working default based on a flattering individual metric.

```sh
python -m pip install -r requirements-research.txt
python compare_arabic_models.py --stage development
# Only after a successful development result:
python compare_arabic_models.py --stage confirmation
```

The output directory preserves completed results and rejects protocol changes
or overwrites. Reproduction uses immutable data/model revisions, file hashes,
recording hashes and a fixed selection seed. No audio is committed to Git.

**Limits:** the public release has no usable speaker identifiers or individual
consent records. Exact-byte separation cannot establish different speakers,
different original utterances, or independence from a pretrained detector's own
training corpus. Any result remains exploratory and specific to this corpus.
Both detectors use large XLS-R encoders; testing the alternative requires a
separate full model download. A proper consented Arabic
corpus is still needed for validated threshold fitting and optional fine-tuning.

## Lightweight public adaptation

The predefined XLS-R candidate failed development: accuracy increased from
62.50% to 67.19%, but fake recall fell from 46.88% to 40.63%. No fresh test
confirmation was run for that candidate and it did not replace the application.

`train_public_head.py` performs a separate experimental adaptation with a frozen
version of the existing encoder and projector. It selects 128 real and 128 fake
public training clips, excluding the reserved 64 development clips and exact
matches with the entire publisher test partition. Each training clip supplies
original, 20 dB noise and 32 kbps MP3 features. A fixed logistic regression
(`C=0.1`) learns a new 256-feature classifier; its scaling is folded into the
saved weights. Neither test clips nor development clips fit the head.

The head is exported as small JSON numeric arrays, bound to the exact model
revision, feature dimension and label index. The runtime rejects nonfinite or
mismatched weights. The head checksum enters model identity, so calibration
from another classifier cannot be silently reused. No executable pickle is loaded.

Development must pass the same frozen gain criteria before scoring the fresh
256-clip confirmation selection. Confirmation also checks digital robustness
and verifies that the installed runtime head matches offline predictions. The
frozen encoder remains unchanged; head-only adaptation is not full encoder
fine-tuning or a completed consented, speaker-independent Arabic study.

```sh
python train_public_head.py --stage fit
python train_public_head.py --stage confirmation
```
