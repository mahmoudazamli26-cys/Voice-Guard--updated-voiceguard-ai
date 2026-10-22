# Security and privacy

This is an educational research prototype, not a forensic or identity verification service.
Report vulnerabilities privately through GitHub's **Report a vulnerability** feature when enabled by the repository owner. Do not post private recordings or exploitable details in a public issue. If that feature is unavailable, ask the repository owner for a private reporting channel without disclosing the vulnerability.

## Controls
- Same-origin frontend/API; no permissive CORS. Restrictive CSP, `nosniff`, no-referrer, no-store, frame restrictions, microphone-only permission policy.
- Bounded request body, one file, bounded decoded duration, FFmpeg network protocols disabled, decode timeout and one concurrent inference. Per-direct-peer rate limits bound repeated requests; no audio filenames or content are logged.
- Uploads stay in memory, including multipart parsing. The browser requests consent. The application retains neither audio nor result reports; reports download only at the user's request. Model cache and aggregate server event logs are separate from audio.
- Deepfake model revisions pinned, no remote code, safetensors required. The separate speech gate uses a bundled, fixed-path Silero TorchScript model verified against its pinned SHA-256 before loading; uploaded files are never loaded as model artifacts. Its recurrent state and audio context are reset after every recording. Calibration must match the configured model revisions and analysis settings.
- Container runs as a non-root user with a single exposed service; Compose adds a read-only root filesystem, resource limits, and dropped capabilities.
- CI runs tests, Bandit and dependency auditing. Dependabot proposes updates; review and test them rather than blindly merging.

## Deployment limits
Use HTTPS at a trusted reverse proxy for any non-local deployment. Add authentication, an ingress request-size cap, connection limits, request timeouts, and a shared rate limiter before exposing to untrusted users. The built-in limiter is process-local and uses the direct peer (not forwarded headers); a reverse proxy may group all clients together. Keep one worker for the in-process concurrency limit. Uvicorn access logs must stay disabled because query strings and request metadata can be sensitive.

FFmpeg is a native decoder, not a complete sandbox. Use the resource-limited container and keep its OS packages current. A decode timeout limits elapsed time, but a hostile decoder input can still consume resources within that interval. Process memory and disk encryption, crash-dump policy, proxy logs, browser extensions, and host administrators are deployment concerns. Consent is a declaration, not proof of recording ownership.

A file hash in a downloaded report can link recordings; treat it as potentially sensitive metadata. Do not upload reports or raw data to Git by default. Errors do not reveal raw decoder output.

See [STRIDE threat model](docs/THREAT_MODEL.md) and [evaluation protocol](docs/RESEARCH.md).
