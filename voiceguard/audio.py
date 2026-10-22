"""Decode untrusted audio through a bounded, timed FFmpeg subprocess in memory."""
import subprocess
import numpy as np
from scipy.signal import stft

EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.webm'}


def decode_audio(content: bytes, sample_rate: int, max_seconds: float) -> np.ndarray:
    signatures = (content.startswith((b'RIFF', b'ID3', b'fLaC', b'OggS', b'\x1aE\xdf\xa3'))
                  or content[4:8] == b'ftyp'
                  or (len(content) > 1 and content[0] == 255 and content[1] & 224 == 224))
    if not signatures:
        raise ValueError('Unsupported or corrupt audio container')
    # No filenames, shell, network protocols, or external playlist references are used.
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
         '-protocol_whitelist', 'pipe', '-threads', '1', '-i', 'pipe:0',
         '-map', '0:a:0', '-vn', '-t', str(max_seconds + 0.1),
         '-ac', '1', '-ar', str(sample_rate), '-f', 'f32le', 'pipe:1'],
        input=content, capture_output=True, timeout=20, check=False,
    )
    if result.returncode or not result.stdout:
        raise ValueError('Unsupported or corrupt audio')
    audio = np.frombuffer(result.stdout, dtype='<f4').copy()
    if len(audio) > int(max_seconds * sample_rate):
        raise ValueError(f'Audio exceeds the {max_seconds:g}-second limit')
    if len(audio) < int(0.1 * sample_rate) or not np.isfinite(audio).all():
        raise ValueError('Audio must contain at least 0.1 seconds of finite samples')
    return audio


def spectrogram(audio, sample_rate):
    frequencies, times, z = stft(audio, fs=sample_rate, nperseg=512, noverlap=256)
    # Bounded payload, logarithmic display magnitude; not a learned explanation.
    rows = np.linspace(0, len(frequencies) - 1, 64).astype(int)
    cols = np.linspace(0, len(times) - 1, min(240, len(times))).astype(int)
    db = 20 * np.log10(np.maximum(np.abs(z[np.ix_(rows, cols)]), 1e-8))
    db = np.clip((db + 80) / 80, 0, 1)
    return {'values': np.round(db, 3).tolist(), 'max_frequency': sample_rate / 2,
            'duration': round(len(audio) / sample_rate, 3)}
