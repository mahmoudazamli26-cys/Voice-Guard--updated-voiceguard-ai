# Three-page review: implementation and evidence

All three pages of the supplied VoiceGuardAI PDF were reviewed. This checklist separates implemented software from experiments that need real data. The user supplied no labeled dataset. A separate small public Arabic exploration has since been run; it does not meet the consented, speaker-disjoint study requirements.

| PDF recommendation | Implementation | Evidence / remaining requirement |
|---|---|---|
| Sliding-window analysis | 5-second windows, 2.5-second stride, tail coverage, mean/max aggregation, timeline | Real 10-second sample yields three windows; coverage tests pass |
| Evaluation script | `evaluate.py`: accuracy, precision/recall/F1, confusion matrix, ROC, interpolated EER; JSON + PNG | Known-value metrics tests and random-model CLI integration pass; real benchmarks require labeled data |
| Robustness | `robustness.py`: paired MP3 32 kbps, noise at 10/20 dB, 8 kHz channel resampling; physical re-recording manifest support | Public-clip digital degradation measured; eight-clip loudspeaker kit prepared, actual phone recordings pending |
| Arabic testing | Consent-aware manifest, language filtering, speaker-disjoint splits, per-language results and collection protocol; separate public exploration | 128 public ArAD clips scored; 62.5% diagnostic accuracy. Speaker IDs and consent records unavailable; full consented study still pending. See `docs/results/README.md` |
| Calibrated thresholds / abstention | Validation-only calibration, empirical error constraints, matching model/window identity; explicit inconclusive result | Experimental public-clip thresholds fitted and tested; 32/256 decisions, 29 correct, 224 inconclusive. Final consented speaker-independent thresholds remain pending |
| Explanation | Spectrogram and window overlay; optional actual occlusion recomputation with score deltas | Real model masked-inference request passed; sensitivity is not causal attribution |
| Second model / ensemble | Two configurable pinned safetensors models, individual scores, mean window scores, disagreement abstention | Both real models loaded and inferred; sample disagreement correctly abstained. No superiority claim |
| Optional Arabic fine-tuning | `train_arabic.py` for consented data; separate public head-only adaptation in `train_public_head.py` | Public frozen-encoder head trained on 256 clips / 768 variants; fresh clip-level confirmation accuracy 54.69% to 71.88%. Consented full-model speaker-disjoint study still pending |
| STRIDE threat model | `docs/THREAT_MODEL.md` | Assets, actors, boundaries, controls and residual risks documented |
| API abuse tests | `tests/test_api.py` | Empty/large/forged/corrupt/long/repeated requests, consent, busy service, model failure, security headers, no-disk-spooling tested |
| Security automation | Bandit, pip-audit, Dependabot, SECURITY.md, GitHub Actions | Local scans run; workflow files added. Remote GitHub Actions have not been executed here |
| Docker, non-root, one port | Dockerfile and hardened Compose service | See container validation record below |
| Serve frontend through FastAPI | Static frontend mounted at `/`; relative API URL | Real browser upload/report flow passed; no permissive CORS |
| Headers / env config | CSP, nosniff, no-referrer, no-store, permissions policy; validated configuration | Header tests pass; no credentials in repository |
| API quality | `/health`, Pydantic response, lifespan loading, structured safe event logging, versioned route | Real health/inference and model-unavailable behavior verified |
| Privacy | Bounded in-memory parsing and FFmpeg pipes, explicit consent, no audio/filename logs | No-spooling tests include an audio file larger than the default 1 MiB spool threshold |
| Accessibility | Native visible file input, focus indicators, skip link, live regions, reduced-motion support, keyboard-scrollable table | English and Arabic axe WCAG A/AA scans pass in tested states |
| Small text / header overlap | Header tagline increased to 12 px; content offset tracks actual fixed-header height | Original logo dimensions, branding and colors preserved; navigation can wrap without covering content |
| Arabic/English and RTL | Language switch covers content, guidance and decisions | Browser RTL and mobile checks pass |
| Drag/drop and microphone | Drop handler, permission-gated MediaRecorder, stop/time/size controls | Real Chromium flow with fake microphone device passes; WebM analyzed by actual API |
| Client size/duration checks / progress | Local decode check, server-independent checks, real XHR upload progress and indeterminate inference progress | Browser upload and recording checks pass |
| Downloadable report | JSON includes input SHA-256, timestamp, model identities, scores, windows and limitations | Browser download parsed and checked |
| Assets / explicit font | Same logo served as lossless WebP; preloaded local WOFF2 font applied across the page | Logo 40.4% smaller; font 66.0% smaller. Pixels/transparency and all 5,918 font mappings preserved; no third-party font requests |
| “What should I do?” guidance | Callback, private family phrase, no money/codes based only on voice | English and Arabic guidance displayed |

## Local validation record

- 28 Python tests passed, including full CLI plumbing with a tiny random model and synthetic tones. Those fixture labels and metrics are software tests, not Arabic recordings or research evidence.
- Real pretrained model inference and occlusion passed on the bundled, unlabeled 10-second recording. No authenticity claim is made about it.
- Real two-model inference passed, and disagreement yielded `inconclusive`.
- Chromium: upload, inference result, JSON download, microphone recording, drag/drop, mobile RTL layout, and English/Arabic axe checks passed. Zero tested WCAG A/AA violations; automated scanning is not a complete accessibility certification.
- Runtime dependency audit: no known vulnerabilities in auditable installed packages after upgrades. PyPI cannot identify the `torch` `+cpu` build, so the corresponding upstream `torch==2.14.1` was audited separately and passed. Direct pinned requirements are also audited separately.
- Bandit: no medium/high findings. Low-severity subprocess/import warnings concern fixed-argument FFmpeg calls with no shell; training randomness is for reproducibility, not cryptography. These remain visible rather than suppressed.
- The reusable cloud installation/startup draft was updated to install the new requirements and serve the UI/API together. Saving the draft does not publish the environment.

## What cannot be finished without data

No consented labeled Arabic dataset was supplied. Therefore final threshold fitting, a consented speaker-independent Arabic study, physical loudspeaker re-recording results, and consented full-model fine-tuning remain **unrun**. Public ArAD inference and head-only adaptation measurements are recorded separately in `docs/results/README.md` and `docs/results/model-improvement/README.md`, with their limitations; they do not complete those pending requirements. The implementation and reproducible commands are ready in `docs/RESEARCH.md`; gathering real data cannot be substituted with invented results. Verify Arabic TTS support, model license and speaker consent before generating data. XTTS was a suggestion in the review, not a dependency verified or bundled here.

## Container validation

The Docker image built successfully with TLS and APT signature verification preserved. The cloud builder needed its existing proxy DNS mapping, proxy build arguments and trusted CA supplied through a BuildKit secret. Runtime uses UID 10001. The writable named model-cache directory is owned by that user. A separate read-only, resource-limited container was started with the already-downloaded public model cache; health and real audio inference passed locally. This verifies cached-model runtime, not a new online download in a fresh Compose volume or remote deployment.

## Original design restoration

At the user's request, the original Reaper AI header, hero, footer, PNG logo and base stylesheet were restored. New controls are scoped to the middle analysis panels, and Arabic direction applies only there. Browser checks report three existing footer contrast findings (4.2:1 versus 4.5:1); those exact legacy findings remain visible and documented because the footer must stay unchanged. New accessibility findings still fail checks. Original markup/assets are checked against frontend.zip. Earlier zero-finding screenshots describe the prior redesigned UI, not this restored version.

## Model label and checkbox placement

At the user's request, the main card now displays REAL AUDIO DETECTED or FAKE AUDIO DETECTED for the higher-scoring class, explicitly labeled MODEL PREDICTION. A short note explains calibration limitations or model disagreement; silence and exact ties still abstain. Downloaded reports include `model_prediction` separately from the unchanged API calibration/abstention `prediction`. Consent and optional explanation checkboxes are stacked directly above Analyze. The original header, hero and footer remain preserved.

## Simplified result card

At the user's request, the circular percentage display is kept and only the model-name score list is removed from the page. The circle, result text, status dot, panel border and horizontal line are red for fake, green for real and orange for inconclusive. Model details and scores remain in the downloaded report. Header, footer and stacked checkbox placement are preserved.

The retained circle is labeled AI CONFIDENCE, with Model confidence score beneath it. Its percentage and arc show the higher-scoring predicted class (real or fake); the horizontal line still tracks the fake-class score. Silence or tied scores display no confidence percentage.

## Faster inference and original result wording

Normal inference now batches up to three equal-length windows without dropping any window or changing aggregation. CPU threads default to at most four, respecting an existing OMP_NUM_THREADS value; VG_CPU_THREADS and VG_INFERENCE_BATCH_SIZE can override those settings. Explanation still performs the actual masked-window computation and remains optional; its masked windows use the serial path because batching did not improve measured CPU latency. The result card matches the original THREAT ASSESSMENT heading and real/fake classification sentence, with LOW / MEDIUM / HIGH line labels. Uncertain results use orange; fake remains red and real green. Display colors indicate the predicted category, not newly fitted validation thresholds.

Cloud timing on the included 10-second sample: warm normal inference was approximately 3.3–3.4 seconds with four CPU threads; optional occlusion required roughly 11–12 seconds. Cold/warm timings varied substantially, so no fixed laptop speedup is promised. Batched and serial scores matched to displayed precision, including occlusion deltas. Peak RSS in the benchmark was about 2.1 GiB.

## No-speech guard

The API runs a bundled, checksum-verified Silero voice activity detector before real/fake inference. It requires at least 250 ms of consecutive speech; silence, tested microphone-like noise, hum and steady tones return `speech_detected: false`, `decision_reason: no_speech` and an inconclusive outcome with empty score/window/model lists. Classification and muting analysis are skipped. The UI shows NO SPEECH DETECTED and a retry instruction in English or Arabic, clears previous scores, and uses the orange status color. Spoken sample recordings still pass. A missing or modified VAD model fails readiness rather than bypassing the guard. This is a pretrained heuristic, not a guarantee against all noise or a validated Arabic benchmark. It applies to the user-facing API; raw classifier research workflows remain unchanged. Model licensing and verified wheel provenance are bundled in voiceguard/assets.

Validation of the speech guard: 42 Python tests passed. Browser checks confirmed speech upload/recording still works, a silent upload shows no-speech feedback with no stale score, and English/Arabic switching preserves that outcome. Known contrast findings in the unchanged original footer remain documented.

## Public Arabic exploration, 20 October 2026

The pinned public ArAD test partition was downloaded; no audio is committed.
On a fixed balanced 128-clip subset the current model achieved 62.50% diagnostic
accuracy, 45.31% fake recall and 43.75% interpolated EER. Paired digital robustness
was run on 32 clips. The two-model mean on the same 128 clips achieved 46.09%
diagnostic accuracy with 53 model disagreements; no ensemble improvement is
claimed. These are raw-score metrics before speech gating or abstention, not
calibrated application decisions. Source checksums, sample hashes, scores, plots,
limitations and reproduction commands are in `docs/results/README.md`. Individual
consent and speaker groups are absent, so calibration/fine-tuning remain pending.
45 Python tests passed; the research dependency audit and medium/high scan passed.
No frontend, application thresholds, or default model configuration changed.

## Experimental public Arabic head adaptation

A predefined XLS-R candidate failed development and was not substituted. A
separate head-only adaptation used 256 public ArAD training clips with original,
20 dB noise and MP3 variants. Its frozen-encoder development check passed. On
256 fresh test clips excluding all previously reviewed recordings, matched
accuracy increased from 54.69% to 71.88%, fake recall from 36.72% to 61.72%, and
real recall from 72.66% to 82.03%. All tested digital perturbations improved on
the predefined 16-clip robustness subset. No consent or speaker independence is
asserted for the public corpus, and the classifier still missed 49/128 fakes.

The approximately 7 KB numeric head is an opt-in `experimental-arabic` profile;
the general default, frontend layout and speech gate are preserved. The Windows
launcher is `start_arabic.bat`. Adapted model checksums enter both calibration
identity and JSON reports. 58 Python tests passed, then 35 related tests passed
after final API metadata changes. Real API speech upload, head checksum,
silence and noise checks passed. See `docs/ARABIC_PROFILE.md` and the complete
paired evidence in `docs/results/model-improvement/README.md`.

## Logo and font optimization

At the user's request the existing PNG logo was losslessly encoded as WebP,
without resizing or redrawing. It decreased from 759,903 to 453,078 bytes;
decoded RGBA pixels, transparency and dimensions are identical. The logo and
favicon now request `new-end.webp`. The local DejaVu Sans font was compressed
from 759,720-byte TTF to 258,324-byte WOFF2, preserving all 5,918 character
mappings and shaping tables, including Arabic. It is preloaded and explicitly
applied across the page with `font-display: swap`; the license remains bundled.
Original source assets remain available for reference but are not requested by
the current page. The layout, colors and original base stylesheet are preserved.

The asset API check and real browser upload/report, microphone, drag/drop,
English/Arabic, mobile and no-speech flows passed. The browser confirmed WOFF2
font loading, WebP logo loading, and no PNG/TTF requests. The three existing
footer contrast findings remain; no new tested accessibility findings appeared.

## Accessibility and fixed-header follow-up

The native upload input remains keyboard accessible. Visible focus styling now
covers header/footer links as well as analysis controls. The result card has a
polite, atomic status live region, announcing the outcome and its description.
Reduced-motion preferences now disable transitions, animations and smooth
scrolling across the whole page, including hover movement on links/buttons.
The header tagline is 12 px instead of 9/8 px. A ResizeObserver measures the
actual fixed header after font loading and viewport changes; body spacing and
anchor scroll clearance follow its height. Narrow navigation can wrap safely.

Browser checks passed at 320, 390, 768 and 1280 px with no header overlap or
horizontal overflow. Keyboard Tab plus Enter opened the native file chooser,
with a visible focus outline. Reduced-motion styles and live-region semantics
were checked. English/Arabic axe checks, microphone, upload, reports, drop and
no-speech flows passed; the three known footer contrast findings remain. These
automated checks are not a complete manual screen-reader certification.


## Experimental calibration and physical-test preparation — 20 October 2026

This update supersedes earlier statements that no thresholds were fitted or that
the UI always substitutes a raw prediction. The original head remains frozen;
new public-clip calibration and fresh testing are documented in [CALIBRATION.md](CALIBRATION.md).
The fresh diagnostic raw accuracy is 72.27%. Calibrated mode decides 32/256 clips
(12.5% coverage), with 29 correct decisions and 224 inconclusive. Three fake clips
were called real. This is experimental evidence, not final production validation.
Speaker identities and individual consent records are unavailable.

The UI now honors calibrated abstention and model disagreement while retaining
its layout, circle, and red/green/orange colors. The original raw Arabic profile
remains available; the new calibrated profile is explicitly selected.

Eight physical-test clips were reserved before scoring and downloaded with exact
waveform verification. [Windows preparation/evaluation launchers](PHYSICAL_TEST.md)
are ready. Actual speaker/microphone recordings and their results remain pending;
software alignment tests are not physical research outcomes.

Verification: 63 Python tests passed; the final profile/configuration subset
passed 21 tests. Browser upload, microphone, no-speech, report, mobile/RTL and
calibrated-decision checks passed. A real-model API smoke check confirmed matching
head/calibration identity, calibrated abstention and silence rejection. Bandit
reported no medium/high findings for the new scripts. Latest commit CI/container
verification is reported separately when completed.


## User-run physical pilot and channel improvement experiment

The uploaded eight-pair report completes the initial physical pilot (user-attested
capture, unknown source speaker independence). Original raw accuracy was 7/8;
phone-capture raw accuracy was 4/8, with 0/4 fake detections at the 0.5 cutoff.
Calibrated phone decisions were six real (including three fake errors), two
inconclusive. This demonstrates failure on the tested setup, not robustness.
Earlier pending-physical statements describe the state before this report.
See [methods, improvement protocol and deployment limits](ROBUSTNESS_IMPROVEMENT.md).
The existing app classifier/calibration remain unchanged during candidate research.
