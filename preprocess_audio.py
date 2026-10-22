
import soundfile as sf
from scipy.signal import resample_poly
import numpy as np

# Read one real audio example
audio, sample_rate = sf.read("audios/real_sample.wav")

print("Before preprocessing")
print("Sample rate:", sample_rate)
print("Audio shape:", audio.shape)

# Step 1: Convert stereo audio to mono
if audio.ndim == 2:
    audio = audio.mean(axis=1)

# Step 2: Resample to 16,000 Hz
target_sample_rate = 16000

if sample_rate != target_sample_rate:
    audio = resample_poly(
        audio,
        target_sample_rate,
        sample_rate
    )

# Step 3: Save the processed audio
sf.write(
    "audios/real_sample_processed.wav",
    audio.astype(np.float32),
    target_sample_rate
)

print("\nAfter preprocessing")
print("Sample rate:", target_sample_rate)
print("Audio shape:", audio.shape)
print("Channels: 1 (mono)")
print("Duration:", round(len(audio) / target_sample_rate, 2), "seconds")
print("Saved processed audio successfully!")
