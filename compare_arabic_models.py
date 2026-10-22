"""Predefined, clip-disjoint public Arabic model comparison (not speaker-disjoint).

No training, threshold tuning, private-consent declarations or app changes.
The previously reviewed 128 clips cannot enter the fresh confirmation subset.
"""
import argparse
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from public_arabic_benchmark import DATASET, REVISION, FILE, select_rows
from robustness import perturb
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import metrics

CANDIDATE = 'Gustking/wav2vec2-large-xlsr-deepfake-audio-classification'
CANDIDATE_REVISION = 'f7050b586236dc910d1157f430def2d0647b02b4'
BASELINE = 'garystafford/wav2vec2-deepfake-voice-detector'
BASELINE_REVISION = 'c66306024a7ede0be291e9c4558b37634782dc4e'
PROTOCOL = {
    'version': 1,
    'development_per_class': 32,
    'confirmation_per_class': 128,
    'robustness_per_class': 8,
    'seed': 20261021,
    'diagnostic_threshold': 0.5,
    'minimum_accuracy_gain': 0.05,
    'minimum_fake_recall_gain': 0.05,
    'maximum_real_recall_loss': 0.02,
    'selection': 'One predefined multilingual candidate versus existing baseline; no threshold fitting.',
    'limitations': 'Public licensed clips; individual consent and speaker independence unverified. No training.',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clip_audio(row, settings):
    audio, rate = sf.read(io.BytesIO(row['audio']['bytes']), dtype='float32')
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if rate != settings.sample_rate:
        divisor = int(np.gcd(rate, settings.sample_rate))
        audio = resample_poly(audio, settings.sample_rate // divisor, rate // divisor).astype(np.float32)
    if len(audio) < 512 or not np.isfinite(audio).all() or len(audio) > settings.max_seconds * settings.sample_rate:
        raise ValueError('Invalid or oversized public audio')
    return audio


def gains_pass(baseline, candidate):
    """Frozen promotion criteria at 0.5, evaluated without tuning any cutoff."""
    real_recall = lambda m: m['confusion_matrix_real_fake'][0][0] / m['real_count']
    return bool(candidate['accuracy'] - baseline['accuracy'] >= PROTOCOL['minimum_accuracy_gain'] - 1e-12
                and candidate['recall'] - baseline['recall'] >= PROTOCOL['minimum_fake_recall_gain'] - 1e-12
                and real_recall(baseline) - real_recall(candidate) <= PROTOCOL['maximum_real_recall_loss'] + 1e-12)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['development', 'confirmation'], required=True)
    parser.add_argument('--output-dir', default='reports/arabic-comparison')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    protocol = {**PROTOCOL, 'candidate': CANDIDATE, 'candidate_revision': CANDIDATE_REVISION,
                'dataset': DATASET, 'dataset_revision': REVISION}
    protocol_hash = digest(json.dumps(protocol, sort_keys=True).encode())
    plan_path = output / 'protocol.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != protocol:
        parser.error('Protocol changed: preserve the previous run and use a new output directory')
    plan_path.write_text(json.dumps(protocol, indent=2) + '\n')
    if (output / f'{args.stage}.json').exists():
        parser.error('Do not overwrite completed results')
    if args.stage == 'confirmation':
        dev = json.loads((output / 'development.json').read_text())
        if dev['protocol_sha256'] != protocol_hash or not dev['criteria_passed']:
            parser.error('Candidate must pass the frozen development criteria before confirmation')
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    test_path = Path(hf_hub_download(DATASET, FILE, repo_type='dataset', revision=REVISION))
    test_rows = pq.read_table(test_path).to_pylist()
    test_hashes = {digest(r['audio']['bytes']) for r in test_rows}
    old = json.loads((Path(__file__).parent / 'docs/results/arad-base.json').read_text())
    if old['revision'] != REVISION:
        parser.error('Previously reviewed data revision must match')
    excluded = {s['sha256'] for s in old['samples']}
    source_files = []
    if args.stage == 'development':
        rows = []
        # Read all training shards for a representative class mix, never the test split.
        for number in range(3):
            filename = f'data/train-{number:05d}-of-00003.parquet'
            path = Path(hf_hub_download(DATASET, filename, repo_type='dataset', revision=REVISION))
            source_files.append({'path': filename, 'sha256': digest(path.read_bytes())})
            rows.extend(pq.read_table(path).to_pylist())
        rows = [r for r in rows if digest(r['audio']['bytes']) not in test_hashes]
        count = PROTOCOL['development_per_class']
    else:
        rows = [r for r in test_rows if digest(r['audio']['bytes']) not in excluded]
        count = PROTOCOL['confirmation_per_class']
        source_files.append({'path': FILE, 'sha256': digest(test_path.read_bytes())})
    selected, duplicates = select_rows(rows, count, PROTOCOL['seed'])
    selection = [{'index_after_exclusions': i, 'publisher_label': label, 'sha256': sha}
                 for i, label, sha in selected]
    # Freeze the selection on disk before loading either model or scoring clips.
    (output / f'{args.stage}-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    samples = {sha: {'sha256': sha, 'label': int(label == 0)} for _, label, sha in selected}
    base_settings = replace(Settings(), model_id=BASELINE, revision=BASELINE_REVISION, cpu_threads=4)
    models = [('baseline', base_settings), ('candidate', replace(base_settings, model_id=CANDIDATE,
                                                                 revision=CANDIDATE_REVISION))]
    results = {}
    for name, settings in models:
        engine = Engine(settings)
        subset_counts = {0: 0, 1: 0}
        conditions = {}
        for number, (index, publisher_label, sha) in enumerate(selected, 1):
            audio = clip_audio(rows[index], settings)
            label = int(publisher_label == 0)
            variants = {'original': audio}
            if args.stage == 'confirmation' and subset_counts[label] < PROTOCOL['robustness_per_class']:
                subset_counts[label] += 1
                variants = perturb(audio, settings.sample_rate, int(sha[:8], 16))
            scores = {condition: engine.analyze(changed)['_raw_fake_score'] for condition, changed in variants.items()}
            samples[sha][name] = scores
            for condition, score in scores.items():
                conditions.setdefault(condition, []).append((label, score))
            print(f'{args.stage}: {name} {number}/{len(selected)}', flush=True)
        results[name] = {'identity': engine.identity(), 'conditions': {
            key: metrics([v[0] for v in values], [v[1] for v in values]) for key, values in conditions.items()}}
        # The original baseline for robust clips must use that same subset.
        robust = [s for s in samples.values() if len(s.get(name, {})) > 1]
        if robust:
            results[name]['robustness_original'] = metrics([s['label'] for s in robust],
                                                           [s[name]['original'] for s in robust])
        del engine
    passed = gains_pass(results['baseline']['conditions']['original'], results['candidate']['conditions']['original'])
    if args.stage == 'confirmation':
        # Reject a gain that sacrifices performance under any tested digital perturbation.
        passed = passed and all(results['candidate']['conditions'][condition]['accuracy'] >=
                                results['baseline']['conditions'][condition]['accuracy']
                                for condition in results['baseline']['conditions'] if condition != 'original')
    report = {'stage': args.stage, 'protocol_sha256': protocol_hash, 'protocol': protocol,
              'source_files': source_files, 'duplicates_removed': duplicates,
              'previously_reviewed_clips_excluded': len(excluded), 'results': results,
              'criteria_passed': bool(passed), 'samples': list(samples.values()),
              'note': 'Diagnostic classifier scores before API speech gating or abstention; no calibration.'}
    (output / f'{args.stage}.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'criteria_passed': passed,
                      'accuracy': {k: v['conditions']['original']['accuracy'] for k, v in results.items()}}, indent=2))


if __name__ == '__main__':
    main()
