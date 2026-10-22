
import soundfile as sf
import os

# The folder containing our audio samples
audio_folder = "audios"

# Inspect both audio files
files = ["real_sample.wav", "fake_sample.wav"]

for filename in files:
    path = os.path.join(audio_folder, filename)

    # Read audio information
    audio, sample_rate = sf.read(path)

    duration = len(audio) / sample_rate

    print("\nFile:", filename)
    print("Sample rate:", sample_rate, "Hz")
    print("Duration:", round(duration, 2), "seconds")
    print("Audio shape:", audio.shape)
    print("Number of channels:", 1 if audio.ndim == 1 else audio.shape[1])
