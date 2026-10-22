
import librosa
import soundfile as sf

input_file = "f7.mp3"
output_file = "f7.wav"

print("Converting audio to 16 kHz WAV...")

audio, sample_rate = librosa.load(
    input_file,
    sr=16000,
    mono=True
)

sf.write(output_file, audio, 16000, subtype="PCM_16")

print("Conversion successful!")
print("Output file:", output_file)
print("Sample rate: 16000 Hz")
