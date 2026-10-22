"""Software simulation checks, not real-world robustness evidence."""
import numpy as np
import pytest

from voiceguard.channel import simulated_playback


def test_channel_is_repeatable_bounded_and_preserves_duration():
    audio = np.random.default_rng(9).normal(0, .1, 32000).astype(np.float32)
    mild = simulated_playback(audio, 16000, 41, 'mild')
    strong = simulated_playback(audio, 16000, 42, 'strong')
    assert mild.shape == audio.shape and strong.dtype == np.float32
    assert np.isfinite(strong).all() and np.max(np.abs(strong)) <= 1
    np.testing.assert_array_equal(mild, simulated_playback(audio, 16000, 41, 'mild'))
    assert not np.array_equal(mild, strong)
    assert not np.array_equal(mild, audio)


def test_channel_rejects_invalid_signal_and_settings():
    for audio in [np.array([]), np.array([np.nan]), np.zeros((2, 20))]:
        with pytest.raises(ValueError):
            simulated_playback(audio, 16000, 1, 'mild')
    with pytest.raises(ValueError):
        simulated_playback(np.ones(20), 16000, 1, 'unknown')
