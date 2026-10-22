"""VoiceGuardAI: same-origin UI and bounded, memory-only audio analysis API."""
import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.datastructures import UploadFile

from voiceguard.audio import EXTENSIONS, decode_audio, spectrogram
from voiceguard.config import Settings
from voiceguard.engine import Engine, DISCLAIMER
from voiceguard.speech import SpeechDetector

logger = logging.getLogger('voiceguard')


class Segment(BaseModel):
    start: float
    end: float
    fake_score: float = Field(ge=0, le=100)
    occlusion_delta: float | None = None


class ModelScore(BaseModel):
    id: str
    revision: str
    fake_score: float = Field(ge=0, le=100)
    head_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class Analysis(BaseModel):
    api_version: str = '1.0.0'
    sha256: str
    prediction: Literal['real', 'fake', 'inconclusive']
    decision_reason: str
    scores: dict[str, float]
    duration: float
    segments: list[Segment]
    models: list[ModelScore]
    calibrated: bool
    disagreement: bool
    aggregation: str
    disclaimer: str
    spectrogram: dict
    speech_detected: bool = True


class RequestLimits:
    """Bound the complete multipart body before parsing; never spool audio to disk."""
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; media-src 'self' blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"),
                    (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'permissions-policy', b'microphone=(self), camera=(), geolocation=()'),
                    (b'cache-control', b'no-store'),
                ]
            await send(message)

        if scope['method'] == 'POST':
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                if len(body) + len(chunk) > self.max_bytes + 65536:
                    return await JSONResponse({'detail': 'Upload is too large'}, status_code=413)(scope, receive, secure_send)
                body.extend(chunk)
                if not message.get('more_body', False):
                    break
            delivered = False

            async def buffered_receive():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}

            return await self.app(scope, buffered_receive, secure_send)
        await self.app(scope, receive, secure_send)


def create_app(settings=None, engine_factory=Engine, speech_detector_factory=SpeechDetector):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        application.state.engine = None
        application.state.speech_detector = None
        application.state.gate = asyncio.Semaphore(1)
        application.state.requests = defaultdict(deque)
        try:
            engine = await run_in_threadpool(engine_factory, settings)
            speech_detector = await run_in_threadpool(speech_detector_factory)
            application.state.engine = engine
            application.state.speech_detector = speech_detector
            logger.info(json.dumps({'event': 'model_ready', 'api_version': '1.0.0'}))
        except Exception as exc:
            # Do not log request metadata, filenames, audio, or credential-bearing errors.
            logger.error(json.dumps({'event': 'model_unavailable', 'error_type': type(exc).__name__}))
        yield
        application.state.engine = None
        application.state.speech_detector = None

    application = FastAPI(title='VoiceGuardAI API', version='1.0.0', lifespan=lifespan,
                          docs_url=None, redoc_url=None)
    application.add_middleware(RequestLimits, max_bytes=settings.max_bytes)

    @application.get('/health')
    async def health():
        ready = application.state.engine is not None
        return JSONResponse({'status': 'ready' if ready else 'model_unavailable',
                             'api_version': '1.0.0', 'calibrated': bool(ready and application.state.engine.calibration),
                             'max_bytes': settings.max_bytes, 'max_seconds': settings.max_seconds,
                             'max_explain_seconds': settings.max_explain_seconds}, status_code=200 if ready else 503)

    @application.post('/analyze', response_model=Analysis, include_in_schema=False)
    @application.post('/api/v1/analyze', response_model=Analysis)
    async def analyze(request: Request, explain: bool = False):
        now = time.monotonic()
        requests = application.state.requests
        # Use direct peers only; do not trust spoofable forwarded headers.
        peer = request.client.host if request.client else 'unknown'
        for key in list(requests):
            if not requests[key] or requests[key][-1] <= now - 60:
                del requests[key]
        if peer not in requests and len(requests) >= 4096:
            raise HTTPException(429, 'Server rate-limit capacity reached', headers={'Retry-After': '60'})
        timestamps = requests[peer]
        while timestamps and timestamps[0] <= now - 60:
            timestamps.popleft()
        if len(timestamps) >= settings.requests_per_minute:
            raise HTTPException(429, 'Too many requests; try again in a minute', headers={'Retry-After': '60'})
        timestamps.append(now)
        if application.state.engine is None:
            raise HTTPException(503, 'Detection model is unavailable')
        if application.state.gate.locked():
            raise HTTPException(429, 'Analysis is busy; try again shortly', headers={'Retry-After': '5'})
        if not request.headers.get('content-type', '').startswith('multipart/form-data'):
            raise HTTPException(415, 'Use a multipart audio upload')
        parser = MultiPartParser(request.headers, request.stream(), max_files=1, max_fields=1,
                                 max_part_size=1024)
        parser.spool_max_size = settings.max_bytes + 65537
        try:
            form = await parser.parse()
        except (MultiPartException, ValueError):
            raise HTTPException(400, 'Invalid multipart upload') from None
        try:
            if form.get('consent') != 'true':
                raise HTTPException(400, 'Consent to process this recording is required')
            file = form.get('file')
            if not isinstance(file, UploadFile):
                raise HTTPException(400, 'Provide one audio file')
            if Path(file.filename or '').suffix.lower() not in EXTENSIONS:
                raise HTTPException(415, 'Unsupported audio extension')
            content = await file.read(settings.max_bytes + 1)
            if len(content) > settings.max_bytes:
                raise HTTPException(413, 'Audio file is too large')
            if not content:
                raise HTTPException(400, 'Audio file is empty')
            async with application.state.gate:
                try:
                    audio = await run_in_threadpool(decode_audio, content, settings.sample_rate, settings.max_seconds)
                    speech_detected = await run_in_threadpool(
                        application.state.speech_detector.contains_speech, audio, settings.sample_rate)
                    if not speech_detected:
                        result = {
                            'prediction': 'inconclusive', 'decision_reason': 'no_speech',
                            'scores': {}, 'duration': round(len(audio) / settings.sample_rate, 3),
                            'segments': [], 'models': [], 'speech_detected': False,
                            'calibrated': application.state.engine.calibration is not None,
                            'disagreement': False, 'aggregation': settings.aggregation,
                            'disclaimer': DISCLAIMER,
                        }
                    else:
                        if explain and len(audio) / settings.sample_rate > settings.max_explain_seconds:
                            raise HTTPException(422, f'Occlusion explanation is limited to {settings.max_explain_seconds:g} seconds')
                        result = await run_in_threadpool(application.state.engine.analyze, audio, explain)
                        result['speech_detected'] = True
                    result['spectrogram'] = await run_in_threadpool(spectrogram, audio, settings.sample_rate)
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from None
                except HTTPException:
                    raise
                except Exception as exc:
                    logger.error(json.dumps({'event': 'analysis_failed', 'error_type': type(exc).__name__}))
                    raise HTTPException(500, 'Audio analysis failed') from None
            result['sha256'] = hashlib.sha256(content).hexdigest()
            return result
        finally:
            await form.close()

    application.mount('/', StaticFiles(directory=settings.frontend, html=True), name='frontend')
    return application


app = create_app()
