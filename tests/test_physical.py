"""Software-only waveform/alignment fixtures, never physical-test evidence."""
import hashlib
import io

import numpy as np
import pytest
import soundfile as sf

from physical_loudspeaker_test import align_recording, verify_wave, evaluate


def test_alignment_uses_content_despite_padding_gain_dc_and_polarity():
    rng = np.random.default_rng(42)
    original = rng.normal(0, .1, 8000).astype(np.float32)
    played = -.6 * original + .05 + rng.normal(0, .001, len(original))
    recording = np.r_[np.zeros(1200), played, np.zeros(2000)]
    aligned, offset, correlation = align_recording(original, recording)
    assert offset == 1200 and correlation > .99
    assert len(aligned) == len(original)
    assert aligned == pytest.approx(played, abs=1e-7)


def test_alignment_rejects_missing_or_wrong_capture():
    original = np.random.default_rng(31).normal(0, .1, 8000)
    with pytest.raises(ValueError, match='shorter'):
        align_recording(original, original[:100])
    with pytest.raises(ValueError, match='Could not match'):
        align_recording(original, np.zeros(10000))


def test_public_download_requires_exact_decoded_waveform():
    buffer = io.BytesIO()
    sf.write(buffer, np.zeros(16000), 16000, format='WAV')
    audio, _ = sf.read(io.BytesIO(buffer.getvalue()), dtype='float32', always_2d=True)
    clip = {'sample_rate': 16000, 'frames': len(audio), 'channels': 1,
            'pcm_sha256': hashlib.sha256(audio.astype('<f4').tobytes()).hexdigest()}
    assert verify_wave(buffer.getvalue(), clip).shape == (16000,)
    with pytest.raises(ValueError, match='does not match'):
        verify_wave(buffer.getvalue(), {**clip, 'pcm_sha256': '0' * 64})


def test_candidate_report_cannot_replace_baseline_or_escape_folder(tmp_path):
    with pytest.raises(ValueError, match='simple JSON filename'):
        evaluate(tmp_path, {}, '../physical-report.json')
    (tmp_path / 'candidate-report.json').write_text('{}')
    with pytest.raises(ValueError, match='Preserve'):
        evaluate(tmp_path, {}, 'candidate-report.json')
