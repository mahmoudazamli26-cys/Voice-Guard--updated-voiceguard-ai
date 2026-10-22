
import librosa
import soundfile as sf

audio, sr = librosa.load(
    "sampleA.wav",
    sr=16000,
    mono=True
)

# Take the first 10 seconds
short_audio = audio[:10 * 16000]

sf.write(
    "sampleA_short.wav",
    short_audio,
    16000,
    subtype="PCM_16"
)

print("Created sampleA_short.wav")
print(f"Duration: {len(short_audio) / 16000:.2f} seconds")
