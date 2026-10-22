# Eight-pair speaker/phone pilot

`summary.json` contains aggregate results from the user's uploaded local report.
Source IDs, labels and original hashes were checked against the frozen plan;
raw/calibrated metrics were recomputed, and alignment offsets fit within recorded
durations. Phone hashes, individual phone metadata and audio are not published.
Physical capture and new-recording permission are user-attested; source consent
and speaker independence remain unverified. The audio itself was not reviewed.

Raw accuracy fell from 7/8 to 4/8; none of the four phone-captured fake clips
passed the diagnostic 0.5 fake cutoff. Calibrated phone decisions included three
fake clips incorrectly called real. This is evidence of failure on this setup,
not a robustness success. Eight pairs do not characterize other devices/rooms.

These clips are not training or threshold-fitting data. Follow-up candidate
comparisons on them are reviewed diagnostics; fresh physical recordings are
needed for confirmation. See [improvement methods](../../ROBUSTNESS_IMPROVEMENT.md).
