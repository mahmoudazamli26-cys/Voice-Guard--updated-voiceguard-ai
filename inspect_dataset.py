
from datasets import load_dataset, Audio
from collections import Counter
import soundfile as sf
import io

print("Loading the full dataset...")

ds = load_dataset(
    "garystafford/deepfake-audio-detection",
    split="train"
).cast_column("audio", Audio(decode=False))

sample_rates = Counter()
channel_counts = Counter()
labels = Counter()
durations = []

# Inspect every recording
for i, sample in enumerate(ds):
    audio_bytes = sample["audio"]["bytes"]
    audio, sample_rate = sf.read(io.BytesIO(audio_bytes))

    duration = len(audio) / sample_rate
    channels = 1 if audio.ndim == 1 else audio.shape[1]

    sample_rates[sample_rate] += 1
    channel_counts[channels] += 1
    labels[ds.features["label"].names[sample["label"]]] += 1
    durations.append(duration)

    if (i + 1) % 200 == 0:
        print(f"Inspected {i + 1} of {len(ds)} recordings")

print("\n--- FULL DATASET SUMMARY ---")
print("Total recordings:", len(ds))
print("Labels:", labels)
print("Sample rates:", sample_rates)
print("Channel counts:", channel_counts)
print("Shortest recording:", round(min(durations), 2), "seconds")
print("Longest recording:", round(max(durations), 2), "seconds")
print("Average duration:", round(sum(durations) / len(durations), 2), "seconds")
