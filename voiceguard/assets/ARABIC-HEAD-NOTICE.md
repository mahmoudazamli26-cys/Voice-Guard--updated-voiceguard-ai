# Experimental Arabic classifier provenance

`arabic_head.json` contains a newly fitted 256-feature linear classifier and
bias, not source recordings or executable code. It is bound to
`garystafford/wav2vec2-deepfake-voice-detector` revision
`c66306024a7ede0be291e9c4558b37634782dc4e` (Gary A. Stafford; stated Apache-2.0
license). The pretrained encoder and projector are unchanged and downloaded
separately under their own model terms.

Training source: **ArAD / DeepFake-Audio-Rangers**, revision
`9dbe1c09acc5907741dcd8c64d7a1d092ff1886d`.
Dataset card: https://huggingface.co/datasets/DeepFake-Audio-Rangers/Arabic_Audio_Deepfake
Stated dataset license: https://opendatacommons.org/licenses/by/1-0/

256 balanced publisher-training clips produced 768 original/noisy/compressed
feature vectors. Development and all publisher test byte hashes were excluded
from fitting. Individual consent records and speaker identifiers were unavailable;
no speaker-independent or individual-consent claim is made. The head includes
its source revision and canonical training-selection/protocol hashes. Exact
selection and paired before/after reports are in `docs/results/model-improvement`.

Use is opt-in and experimental. The dataset covers mainly short Levantine/RVC
clips. Class scores are not authenticity guarantees or probabilities of fraud.
No final abstention calibration or physical re-recording validation is bundled.
