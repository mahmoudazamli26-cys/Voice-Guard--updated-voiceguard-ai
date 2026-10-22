import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from app import create_app
from voiceguard.engine import Engine
from conftest import FakeDetector, FakeSpeechDetector


def post(client, payload, name='sample.wav', **kwargs):
    return client.post('/api/v1/analyze', files={'file': (name, payload, 'audio/wav')},
                       data={'consent': 'true'}, **kwargs)


def test_full_upload_and_privacy(client, wav):
    content = wav()
    response = post(client, content)
    assert response.status_code == 200, response.text
    result = response.json()
    import hashlib
    assert result['sha256'] == hashlib.sha256(content).hexdigest()
    assert result['prediction'] == 'inconclusive'
    assert result['decision_reason'] == 'uncalibrated'
    assert result['duration'] == 0.4
    assert result['scores']['fake'] > 0
    assert result['segments'][0]['start'] == 0
    assert 'filename' not in result
    assert len(result['spectrogram']['values']) == 64


def test_empty(client):
    assert post(client, b'').status_code == 400


def test_large_body(client):
    assert post(client, b'X' * 100000).status_code == 413


def test_large_file(client):
    assert post(client, b'X' * 33000).status_code == 413


def test_forged_extension(client):
    assert post(client, b'<script>alert(1)</script>').status_code == 422


def test_corrupt_container(client):
    assert post(client, b'RIFF' + bytes(100)).status_code == 422


def test_unsupported_extension(client, wav):
    assert post(client, wav(), 'file.exe').status_code == 415


def test_duration_limit(client):
    buffer = io.BytesIO()
    sf.write(buffer, np.ones(24000) * 0.1, 8000, format='FLAC')
    response = post(client, buffer.getvalue(), 'long.flac')
    assert response.status_code == 422
    assert 'second' in response.json()['detail']


def test_consent_required(client, wav):
    response = client.post('/api/v1/analyze', files={'file': ('a.wav', wav())})
    assert response.status_code == 400


def test_no_disk_spooling(client, wav, monkeypatch):
    from tempfile import SpooledTemporaryFile
    def fail(*args, **kwargs):
        raise AssertionError('Audio was spooled to disk')
    monkeypatch.setattr(SpooledTemporaryFile, 'rollover', fail)
    assert post(client, wav()).status_code == 200


def test_repeated_requests(settings, wav):
    settings = replace(settings, requests_per_minute=2)
    with TestClient(create_app(settings, lambda s: Engine(s, [FakeDetector()]), speech_detector_factory=FakeSpeechDetector)) as client:
        assert post(client, wav()).status_code == 200
        assert post(client, wav()).status_code == 200
        response = post(client, wav())
        assert response.status_code == 429
        assert response.headers['retry-after'] == '60'


def test_health_and_security_headers(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ready'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert response.headers['cache-control'] == 'no-store'
    assert 'access-control-allow-origin' not in response.headers


def test_frontend_and_assets(client):
    for path in ['/', '/script.js', '/style.css', '/enhancements.css', '/new-end.png', '/new-end.webp', '/logo.svg', '/font.ttf', '/font.woff2']:
        assert client.get(path).status_code == 200
    assert client.get('/../app.py').status_code == 404
    import re
    import zipfile
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(root/'frontend.zip') as archive:
        original=archive.read('frontend/frontend/index.html').decode()
        current=client.get('/').text
        # Only the logo encoding changes in the original header markup.
        normalize=lambda text:'\n'.join(line.rstrip() for line in text.replace('./new-end.webp','./new-end.png').splitlines())
        for tag in ['header','footer']:
            pattern=rf'<{tag}\b.*?</{tag}>'
            assert normalize(re.search(pattern,current,re.S).group())==normalize(re.search(pattern,original,re.S).group())
        assert re.search(r'<section class="hero">.*?</section>',current,re.S).group()==re.search(r'<section class="hero">.*?</section>',original,re.S).group()
        assert client.get('/style.css').content==archive.read('frontend/frontend/style.css')
        assert client.get('/new-end.png').content==archive.read('frontend/frontend/new-end.png')


def test_model_failure_keeps_ui_available(settings, wav):
    def fail(settings):
        raise RuntimeError('private diagnostic')
    with TestClient(create_app(settings, fail)) as client:
        assert client.get('/health').status_code == 503
        assert client.get('/').status_code == 200
        response = post(client, wav())
        assert response.status_code == 503
        assert 'private diagnostic' not in response.text


def test_occlusion(client, wav):
    response = post(client, wav(), params={'explain': 'true'})
    assert response.status_code == 200
    assert response.json()['segments'][0]['occlusion_delta'] > 0


def test_malformed_multipart(client):
    response = client.post('/api/v1/analyze', content=b'broken', headers={'content-type': 'multipart/form-data'})
    assert response.status_code == 400


def test_busy_rejected(settings, wav):
    import threading
    entered, release = threading.Event(), threading.Event()
    class SlowDetector(FakeDetector):
        def score(self, audio, sample_rate):
            entered.set()
            if not release.wait(10):
                raise RuntimeError('test synchronization timed out')
            return super().score(audio, sample_rate)
    with TestClient(create_app(settings, lambda s: Engine(s, [SlowDetector()]), speech_detector_factory=FakeSpeechDetector)) as client:
        with ThreadPoolExecutor() as pool:
            first = pool.submit(post, client, wav())
            try:
                assert entered.wait(10)
                assert post(client, wav()).status_code == 429
            finally:
                release.set()
            assert first.result().status_code == 200


def test_large_audio_never_rolls_to_disk(wav, monkeypatch):
    from tempfile import SpooledTemporaryFile
    from voiceguard.config import Settings
    settings=Settings(max_bytes=2*1024*1024,max_seconds=60,requests_per_minute=100)
    payload=wav(seconds=40)
    assert len(payload)>1024*1024
    def fail(*args,**kwargs):raise AssertionError('Audio must remain in memory beyond default spool threshold')
    monkeypatch.setattr(SpooledTemporaryFile,'rollover',fail)
    with TestClient(create_app(settings,lambda s:Engine(s,[FakeDetector()]),speech_detector_factory=FakeSpeechDetector)) as client:
        assert post(client,payload).status_code==200
