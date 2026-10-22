import io
from dataclasses import replace
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from app import create_app
from voiceguard.config import Settings
from voiceguard.engine import Engine


class FakeDetector:
    def score(self, audio, sample_rate):
        return float(np.clip(np.mean(np.abs(audio)) * 2, 0, 1))


class FakeSpeechDetector:
    """Accept synthetic tone fixtures when testing unrelated API behavior."""
    def contains_speech(self, audio, sample_rate=16000): return True


@pytest.fixture
def settings():
    return Settings(max_bytes=32000, max_seconds=2, requests_per_minute=100)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, lambda s: Engine(s, [FakeDetector()]), speech_detector_factory=FakeSpeechDetector)) as client:
        yield client


@pytest.fixture
def wav():
    def make(seconds=0.4, rate=16000):
        buffer = io.BytesIO()
        audio = np.sin(np.arange(int(seconds * rate)) * 2 * np.pi * 440 / rate) * 0.2
        sf.write(buffer, audio, rate, format='WAV')
        return buffer.getvalue()
    return make
