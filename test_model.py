
import os
import torch
import librosa
from transformers import (
    AutoModelForAudioClassification,
    AutoFeatureExtractor,
)

MODEL_ID = "garystafford/wav2vec2-deepfake-voice-detector"

print("Loading VoiceGuardAI model...")

model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)

extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
model.eval()

print("Model loaded successfully!")
print("Model labels:", model.config.id2label)
print("MODEL NAME:", MODEL_ID)
print("SAMPLE RATE:", extractor.sampling_rate)

audio_path = input(
    "\nEnter the full path to your audio file: "
).strip().strip('"')

if not os.path.isfile(audio_path):
    print("Error: File not found. Check the path and try again.")
    raise SystemExit(1)

try:
    print("\nLoading audio...")

    audio, _ = librosa.load(
        audio_path,
        sr=16000,
        mono=True
    )
    duration = len(audio) / 16000

    print(f"Audio duration: {duration:.2f} seconds")
    print(f"Sample rate: 16000 Hz")
    print(f"Audio samples: {len(audio)}")

    if len(audio) == 0:
        raise ValueError("The audio file is empty.")
    print("Model expected sample rate:", extractor.sampling_rate)
    print("Audio array shape:", audio.shape)
    print("Audio data type:", audio.dtype)
    print("Audio duration:", len(audio) / extractor.sampling_rate)

    inputs = extractor(
        audio,
        sampling_rate=16000,
        return_tensors="pt"
    )

    print("Analyzing audio...")

    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.softmax(
            outputs.logits, dim=-1
        )[0]

    predicted_id = int(probabilities.argmax().item())
    predicted_label = model.config.id2label[predicted_id]

    print("\n===== VoiceGuardAI Results =====")
    print("File:", os.path.basename(audio_path))
    print("Prediction:", predicted_label)
    print(
        f"Model score: "
        f"{probabilities[predicted_id].item() * 100:.2f}%"
    )
    print("\nAll class scores:")

    for index, score in enumerate(probabilities):
        label = model.config.id2label[index]
        print(f"{label}: {score.item() * 100:.2f}%")

    print("================================")

except Exception as error:
    print(f"\nAudio analysis failed: {error}")
