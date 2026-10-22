# Synthetic channel candidate — experimental

Development completed on 64 public clips, using a fixed classifier trained on
256 distinct training clips × original/mild/strong conditions. This is a
frozen-encoder head experiment. It does not establish physical robustness.

| Development condition | Current Arabic head | Candidate |
|---|---:|---:|
| Original | 73.44% | 71.88% |
| Simulated mild channel | 59.38% | 65.63% |
| Simulated strong channel | 57.81% | 65.63% |

The predeclared development rule passed. Fresh 128-clip confirmation is still
running; no confirmation or physical improvement is claimed here yet.
The candidate is a research artifact, not installed in the application, and the
previous head's calibration must not be used with it.

`selection.json` freezes all source IDs/checksums; `fit.json` contains measured
development scores and metrics; `candidate_head.json` contains the numeric
classifier. Audio/features are not redistributed. Unknown speaker independence
and individual consent limit these public clip-level findings.

See [the full improvement protocol](../../ROBUSTNESS_IMPROVEMENT.md).
