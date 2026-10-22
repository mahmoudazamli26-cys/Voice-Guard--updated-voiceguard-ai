"""Deterministic synthetic room/channel augmentation, never physical capture."""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt


def simulated_playback(audio, rate, seed, severity):
    """Vary bandwidth, echoes, decay, noise and gain without using class labels.

    A simple randomized impulse response is a training stressor, not a measured
    room response or a validated simulation of any user's phone or loudspeaker.
    Preserve duration and never normalize away all channel distortion.
    """
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
        raise ValueError('Expected finite nonempty mono audio')
    if rate < 8000 or severity not in {'mild', 'strong'}:
        raise ValueError('Use a supported sample rate and mild/strong channel')
    rng = np.random.default_rng(seed)
    strong = severity == 'strong'
    low = rng.uniform(120, 280) if strong else rng.uniform(60, 140)
    high = rng.uniform(2800, 4200) if strong else rng.uniform(4200, 6500)
    high = min(high, rate * .45)
    filtered = sosfilt(butter(3, [low, high], btype='bandpass', fs=rate, output='sos'), audio)
    duration = rng.uniform(.18, .38) if strong else rng.uniform(.06, .18)
    impulse = np.zeros(int(duration * rate) + 1)
    impulse[0] = 1
    for delay in rng.uniform(.008, duration, size=18 if strong else 8):
        index = int(delay * rate)
        impulse[index] += rng.choice([-1., 1.]) * rng.uniform(.08, .35) * np.exp(-3 * delay / duration)
    impulse /= np.sqrt(np.sum(impulse ** 2))
    changed = fftconvolve(filtered, impulse)[:len(audio)]
    rms = max(float(np.sqrt(np.mean(changed ** 2))), 1e-8)
    snr = rng.uniform(12, 22) if strong else rng.uniform(24, 35)
    noise = rng.normal(size=len(audio))
    noise *= rms / (max(float(np.sqrt(np.mean(noise ** 2))), 1e-8) * 10 ** (snr / 20))
    changed = (changed + noise) * rng.uniform(.5, 1.25)
    return np.clip(changed, -1, 1).astype(np.float32)
