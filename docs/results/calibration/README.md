# Experimental public Arabic calibration evidence

See [the study explanation](../../CALIBRATION.md) for methods and limitations.
These are measured public-clip results, not a consented speaker-independent study.

- `selection.json`: frozen protocol, checksums and reserved validation/test clips.
- `calibrate.json`: validation scores and speech eligibility; 128 clips, 13 decided.
- `calibration.json`: fitted thresholds and exact model/head/window identity.
- `test.json`: fresh 256-clip test and paired 16-clip digital robustness results.
- `physical_plan.json`: eight reserved public clips; no physical capture results.

Test: 32/256 decided, 29/32 correct, 224/256 inconclusive, three fake clips called
real and zero real clips called fake. Raw diagnostic accuracy was 72.27%.
Most small robustness conditions abstain on all or nearly all clips; do not claim
perfect accuracy or robustness. All rates are small-sample observed estimates.

Source: DeepFake-Audio-Rangers/Arabic_Audio_Deepfake, pinned revision
`9dbe1c09acc5907741dcd8c64d7a1d092ff1886d`, publisher-stated ODC-By-1.0 license.
Speaker IDs, individual consent and pretrained-data overlap are unknown.
No audio is committed. Physical results require actual phone recordings using
[the guide](../../PHYSICAL_TEST.md); no result is invented from this plan.
