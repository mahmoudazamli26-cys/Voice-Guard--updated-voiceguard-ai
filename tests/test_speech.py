"""Real pretrained speech gate tests, including the API boundary."""
import io
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from app import create_app
from voiceguard.audio import decode_audio
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.speech import SpeechDetector


@pytest.fixture(scope='module')
def speech_detector():
    return SpeechDetector()


@pytest.mark.parametrize('kind',['silence','quiet_noise','loud_noise','hum','tone','dc'])
def test_no_speech_rejected(speech_detector,kind):
    rate=16000;t=np.arange(3*rate)/rate
    examples={
        'silence':np.zeros(len(t)),
        'quiet_noise':np.random.default_rng(7).normal(0,.005,len(t)),
        'loud_noise':np.random.default_rng(8).normal(0,.1,len(t)),
        'hum':.08*np.sin(2*np.pi*60*t),
        'tone':.2*np.sin(2*np.pi*440*t),
        'dc':np.ones(len(t))*.1,
    }
    assert speech_detector.contains_speech(examples[kind].astype(np.float32)) is False


@pytest.mark.parametrize('name',['sampleA_short.wav','sampleA2.wav'])
def test_spoken_recordings_pass(speech_detector,name):
    path=Path(__file__).resolve().parents[1]/name
    audio=decode_audio(path.read_bytes(),16000,120)
    assert speech_detector.contains_speech(audio) is True
    # A previous voice must not contaminate the next quiet microphone recording.
    noise=np.random.default_rng(12).normal(0,.003,48000).astype(np.float32)
    assert speech_detector.contains_speech(noise) is False


def test_api_skips_classifier_and_explanation_for_no_speech(speech_detector):
    class MustNotRun:
        def score(self,*args):raise AssertionError('No-speech input reached the classifier')
    settings=Settings(requests_per_minute=100)
    with TestClient(create_app(settings,lambda s:Engine(s,[MustNotRun()]),
                               speech_detector_factory=lambda:speech_detector)) as client:
        for kind,audio in [('silence',np.zeros(48000)),('noise',np.random.default_rng(9).normal(0,.005,48000))]:
            buffer=io.BytesIO();sf.write(buffer,audio,16000,format='WAV')
            response=client.post('/api/v1/analyze?explain=true',data={'consent':'true'},
                                 files={'file':(kind+'.wav',buffer.getvalue(),'audio/wav')})
            assert response.status_code==200,response.text
            result=response.json()
            assert result['speech_detected'] is False
            assert result['decision_reason']=='no_speech'
            assert result['prediction']=='inconclusive'
            assert result['scores']=={} and result['segments']==[] and result['models']==[]


def test_api_speech_continues_to_classification(speech_detector):
    class Fixed:
        def score(self,*args):return .75
    settings=Settings(requests_per_minute=100)
    with TestClient(create_app(settings,lambda s:Engine(s,[Fixed()]),
                               speech_detector_factory=lambda:speech_detector)) as client:
        path=Path(__file__).resolve().parents[1]/'sampleA_short.wav'
        with path.open('rb') as file:
            response=client.post('/api/v1/analyze',data={'consent':'true'},files={'file':('speech.wav',file,'audio/wav')})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['speech_detected'] is True
        assert result['scores']['fake']==75 and len(result['segments'])==3


def test_modified_speech_model_is_not_loaded(monkeypatch):
    monkeypatch.setattr('voiceguard.speech.MODEL_SHA256','0'*64)
    with pytest.raises(ValueError,match='checksum mismatch'):SpeechDetector()


def test_missing_speech_detector_fails_closed():
    class Fixed:
        def score(self,*args):return .25
    def broken():raise OSError('model missing')
    with TestClient(create_app(Settings(),lambda s:Engine(s,[Fixed()]),speech_detector_factory=broken)) as client:
        assert client.get('/health').status_code==503
        assert client.get('/').status_code==200
