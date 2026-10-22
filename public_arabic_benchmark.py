"""Exploratory ArAD benchmark, separate from consented speaker-disjoint research.

Install requirements-research.txt first. Public availability and the dataset's
stated license are not evidence of individual speaker consent. No training or
threshold fitting is performed, and the application configuration is unchanged.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from evaluate import write_plots
from robustness import perturb
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import metrics
from voiceguard.speech import SpeechDetector

DATASET = 'DeepFake-Audio-Rangers/Arabic_Audio_Deepfake'
REVISION = '9dbe1c09acc5907741dcd8c64d7a1d092ff1886d'
FILE = 'data/test-00000-of-00001.parquet'
LIMITATIONS = [
    'Exploratory balanced subset of the publisher test partition, not a full benchmark.',
    'Speaker IDs and individual consent records are absent from the dataset card.',
    'Speaker independence, duplicate utterance independence and model training overlap are unverified.',
    'Publisher labels are used without independent authenticity verification.',
    'Mostly Levantine Arabic, RVC generation and short cleaned clips limit generalization.',
    'No calibration, fine-tuning, physical re-recording or production threshold changes.',
    'Classifier metrics precede the API speech gate; gate rejection counts are reported separately.',
]


def select_rows(rows, per_class, seed):
    """Select without looking at model scores; discard exact duplicate byte content."""
    unique, seen = [], {}
    for index, row in enumerate(rows):
        label = row['label']
        if label not in (0, 1):
            raise ValueError('Unexpected publisher label')
        digest = hashlib.sha256(row['audio']['bytes']).hexdigest()
        if digest in seen:
            if seen[digest] != label:
                raise ValueError('Conflicting labels on duplicate audio')
            continue
        seen[digest] = label
        unique.append((index, label, digest))
    rng = np.random.default_rng(seed)
    selected = []
    for label in (0, 1):  # publisher: 0=fake, 1=real
        candidates = [r for r in unique if r[1] == label]
        if len(candidates) < per_class:
            raise ValueError('Not enough unique examples per class')
        selected.extend(candidates[int(i)] for i in rng.choice(len(candidates), per_class, replace=False))
    return sorted(selected), len(rows) - len(unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-class', type=int, default=64)
    parser.add_argument('--robustness-per-class', type=int, default=16)
    parser.add_argument('--seed', type=int, default=20261020)
    parser.add_argument('--output', default='reports/public-arabic-exploratory.json')
    args = parser.parse_args()
    if not 2 <= args.per_class <= 1000 or not 0 <= args.robustness_per_class <= args.per_class:
        parser.error('Use 2–1000 samples per class; robustness subset must fit within it')
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    source = Path(hf_hub_download(DATASET, FILE, repo_type='dataset', revision=REVISION))
    rows = pq.read_table(source).to_pylist()
    selected, duplicates = select_rows(rows, args.per_class, args.seed)
    settings = Settings.from_env()
    if settings.calibration:
        parser.error('Run this exploratory benchmark without VG_CALIBRATION')
    engine, speech = Engine(settings), SpeechDetector()
    samples, conditions = [], {}
    robustness_counts = {0: 0, 1: 0}
    for position, (index, publisher_label, digest) in enumerate(selected, 1):
        audio, rate = sf.read(io.BytesIO(rows[index]['audio']['bytes']), dtype='float32')
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        if rate != settings.sample_rate:
            divisor = int(np.gcd(rate, settings.sample_rate))
            audio = resample_poly(audio, settings.sample_rate // divisor, rate // divisor).astype(np.float32)
        if not len(audio) or not np.isfinite(audio).all() or len(audio) > settings.max_seconds * settings.sample_rate:
            raise ValueError(f'Invalid or oversized audio at dataset row {index}')
        label = int(publisher_label == 0)  # metrics: fake=positive
        analysis = engine.analyze(audio)
        score = analysis['_raw_fake_score']
        sample = {'row_index': index, 'sha256': digest, 'label': label,
                  'score': score, 'duration_seconds': len(audio) / settings.sample_rate,
                  'speech_detected': bool(speech.contains_speech(audio, settings.sample_rate)),
                  'model_disagreement': analysis['disagreement'],
                  'model_scores_percent': analysis['models']}
        if robustness_counts[label] < args.robustness_per_class:
            robustness_counts[label] += 1
            sample['robustness_scores'] = {}
            for condition, changed in perturb(audio, settings.sample_rate, int(digest[:8], 16)).items():
                value = score if condition == 'original' else engine.analyze(changed)['_raw_fake_score']
                sample['robustness_scores'][condition] = value
                conditions.setdefault(condition, []).append((label, value, value - score))
        samples.append(sample)
        print(f'Completed {position}/{len(selected)}', flush=True)
    summary = {name: {'metrics': metrics([v[0] for v in values], [v[1] for v in values]),
                     'mean_absolute_score_change': float(np.mean([abs(v[2]) for v in values])),
                     'mean_signed_score_change': float(np.mean([v[2] for v in values]))}
               for name, values in conditions.items()}
    result = {'status': 'exploratory_only', 'dataset': DATASET, 'revision': REVISION,
              'source_url': f'https://huggingface.co/datasets/{DATASET}',
              'attribution': 'ArAD dataset, DeepFake-Audio-Rangers; see dataset card at pinned revision.',
              'stated_license': 'ODC-By-1.0', 'source_file': FILE,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'split': 'publisher test subset', 'seed': args.seed,
              'duplicates_removed_before_sampling': duplicates,
              'limitations': LIMITATIONS, 'identity': engine.identity(),
              'metrics': metrics([s['label'] for s in samples], [s['score'] for s in samples]),
              'model_disagreement_count': sum(s['model_disagreement'] for s in samples),
              'speech_gate_rejections': {name: sum(not s['speech_detected'] for s in samples if s['label'] == label)
                                         for label, name in [(0, 'real'), (1, 'fake')]},
              'robustness': summary, 'samples': samples}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_plots(result, output)
    print(json.dumps({k: v for k, v in result['metrics'].items() if k != 'roc'}, indent=2))


if __name__ == '__main__':
    main()
