"""Memory-only speech gate using a bundled, checksum-verified Silero VAD model."""
import hashlib
import math
from pathlib import Path
import threading

import numpy as np

MODEL_SHA256 = 'e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720'


class SpeechDetector:
    """Require at least 250 ms of consecutive speech before real/fake analysis.

    Speech detection is imperfect: very quiet or heavily distorted speech can be
    missed, and some non-speech can resemble speech. This is not authentication.
    """
    def __init__(self):
        import torch
        model_path = Path(__file__).parent / 'assets' / 'silero_vad.jit'
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError('Speech detector model checksum mismatch')
        self.torch = torch
        # Only this fixed, verified project asset is loaded; never an upload.
        self.model = torch.jit.load(str(model_path), map_location='cpu').eval()
        self.lock = threading.Lock()

    def contains_speech(self, audio, sample_rate=16000):
        if sample_rate != 16000:
            raise ValueError('Speech detector expects 16 kHz audio')
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim != 1 or not np.isfinite(audio).all():
            raise ValueError('Speech detector expects finite mono audio')
        if len(audio) < 4000:
            return False
        # Remove DC only for the energy check; do not amplify microphone noise.
        if float(np.std(audio, dtype=np.float64)) < 1e-5:
            return False
        frame_size = 512
        required_frames = math.ceil(0.25 * sample_rate / frame_size)
        with self.lock, self.torch.inference_mode():
            self.model.reset_states()
            try:
                run = 0
                for start in range(0, len(audio), frame_size):
                    frame = self.torch.from_numpy(audio[start:start + frame_size])
                    if len(frame) < frame_size:
                        frame = self.torch.nn.functional.pad(frame, (0, frame_size - len(frame)))
                    probability = float(self.model(frame, sample_rate).item())
                    if not math.isfinite(probability) or not 0 <= probability <= 1:
                        raise ValueError('Speech detector returned an invalid probability')
                    run = run + 1 if probability >= 0.5 else 0
                    if run >= required_frames:
                        return True
                return False
            finally:
                # Clear recurrent state and audio context after EVERY recording.
                self.model.reset_states()
