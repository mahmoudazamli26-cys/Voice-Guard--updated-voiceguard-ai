# One-page STRIDE threat model

**Assets:** uploaded recordings, consent, model integrity, calibration integrity, service availability, reports and speaker privacy.
**Actors:** a consenting researcher; a malicious uploader; a voice impersonator adapting audio to evade detection; a dependency/model supplier.
**Boundary:** untrusted browser → bounded ASGI ingress → in-memory multipart/parser → restricted FFmpeg → inference engine → JSON/UI. Public model downloads cross a separate supply boundary. A deployment proxy is outside the app boundary.

| STRIDE | Concrete threat | Implemented control | Remaining limit |
|---|---|---|---|
| Spoofing | Cloned caller sounds like a relative; forged upload MIME type | Decode actual container bytes; classify windows; recommend independent callback and verification phrase | Model output does not authenticate a speaker or caller; native container inspection is not forensic verification |
| Tampering | Malformed audio, modified dependency/model/calibration | Bounded decoder, pinned model revision, safetensors, no remote code, identity-bound calibration, CI audits | Supply chain and compromised host remain risks; secure model/cache permissions |
| Repudiation | User denies uploading or claims consent | Explicit consent UI and API flag; downloaded report includes hash/model revision | No identity verification or permanent audit trail by design |
| Information disclosure | Audio leaked via temporary files, logs, third-party fonts | In-memory upload/decode, no audio/filename logging, same-origin local font, no-store | Host memory, proxies and user-retained reports need deployment protections |
| Denial of service | Huge/long/corrupt file, floods, expensive masking | Byte/duration caps, timeout, concurrency cap, per-peer rate limiting, explanation duration cap, Compose CPU/RAM/PID limits | Distributed attacks require ingress controls, authentication and a shared limiter |
| Elevation of privilege | Decoder exploit, unsafe model code | Non-root container, disabled FFmpeg network protocols, dropped capabilities, no remote model code | Native codecs are not fully sandboxed; update OS packages and isolate deployments |

**ML evasion:** compression, noise, channel/resampling changes, dialect shift and unknown generators can alter predictions. `robustness.py` measures paired degradation; Arabic evaluation uses consented speaker-disjoint manifests. Neither testing nor ensembles guarantees robustness. Silent input and model disagreement abstain. Occlusion is a sensitivity visualization, not evidence of causal attribution.
