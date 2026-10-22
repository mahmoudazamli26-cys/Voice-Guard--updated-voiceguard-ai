"""Experimental public-ArAD head adaptation; no speaker-independent claim.

Uses a frozen pretrained encoder/projector and licensed public training clips.
Does not use, or falsify consent fields for, the private manifest workflow.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from compare_arabic_models import BASELINE, BASELINE_REVISION, clip_audio, gains_pass
from public_arabic_benchmark import DATASET, REVISION, FILE, select_rows
from robustness import perturb
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import metrics

PLAN = {'version': 1, 'seed': 20261022, 'train_per_class': 128,
        'development_per_class': 32, 'confirmation_per_class': 128,
        'robustness_per_class': 8, 'C': 0.1,
        'augmentations': ['original', 'noise_20db', 'mp3_32kbps'],
        'selection': 'Fixed logistic regression on frozen classifier-input features; development pass required.',
        'dataset': DATASET, 'dataset_revision': REVISION,
        'base_model': BASELINE, 'base_revision': BASELINE_REVISION,
        'limitations': 'Public licensed data; individual consent and speaker independence unverified. Experimental only.'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['fit', 'confirmation'], required=True)
    p.add_argument('--output-dir', default='reports/public-head')
    p.add_argument('--development-report', default='reports/arabic-comparison/development.json')
    args = p.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / 'protocol.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != PLAN:
        p.error('Protocol changed; preserve the old results and use a new directory')
    plan_path.write_text(json.dumps(PLAN, indent=2) + '\n')
    report_path = out / f'{args.stage}.json'
    if report_path.exists():
        p.error('Completed results cannot be overwritten')
    development = json.loads(Path(args.development_report).read_text())
    dev_hashes = {s['sha256'] for s in development['samples']}
    if len(dev_hashes) != 64:
        p.error('Expected the reserved 64-clip development selection')
    if args.stage == 'confirmation' and not json.loads((out / 'fit.json').read_text())['criteria_passed']:
        p.error('Development must pass before opening the fresh confirmation subset')
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    test_path = Path(hf_hub_download(DATASET, FILE, revision=REVISION, repo_type='dataset'))
    test_rows = pq.read_table(test_path).to_pylist()
    test_hashes = {sha(r['audio']['bytes']) for r in test_rows}
    old = json.loads((Path(__file__).parent / 'docs/results/arad-base.json').read_text())
    reviewed = {s['sha256'] for s in old['samples']}
    if dev_hashes & test_hashes:
        p.error('Development overlaps with publisher test audio')
    settings = replace(Settings(), model_id=BASELINE, revision=BASELINE_REVISION, cpu_threads=4)
    engine = Engine(settings)
    captured = []
    def capture(_module, inputs):
        captured.append(inputs[0].detach().cpu().numpy().copy())
    hook = engine.detectors[0].model.classifier.register_forward_pre_hook(capture)
    def extract(row):
        captured.clear()
        audio = clip_audio(row, settings)
        if len(audio) > settings.sample_rate * settings.window_seconds:
            raise ValueError('This public head study requires single-window clips')
        baseline = engine.analyze(audio)['_raw_fake_score']
        if len(captured) != 1 or captured[0].shape[0] != 1:
            raise ValueError('Expected exactly one classifier input')
        return captured[0][0].copy(), baseline
    sources = [{'path': FILE, 'sha256': sha(test_path.read_bytes())}]
    if args.stage == 'fit':
        rows = []
        for number in range(3):
            filename = f'data/train-{number:05d}-of-00003.parquet'
            path = Path(hf_hub_download(DATASET, filename, revision=REVISION, repo_type='dataset'))
            sources.append({'path': filename, 'sha256': sha(path.read_bytes())})
            rows.extend(pq.read_table(path).to_pylist())
        dev_rows = [r for r in rows if sha(r['audio']['bytes']) in dev_hashes]
        if len(dev_rows) != 64:
            raise ValueError('Reserved development recordings are missing or duplicated')
        pool = [r for r in rows if sha(r['audio']['bytes']) not in test_hashes | dev_hashes]
        selected, duplicates = select_rows(pool, PLAN['train_per_class'], PLAN['seed'])
        selection = [{'sha256': digest, 'label': int(label == 0)} for _, label, digest in selected]
        (out / 'train-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
        features, labels = [], []
        for number, (index, label, digest) in enumerate(selected, 1):
            audio = clip_audio(pool[index], settings)
            if len(audio) > settings.sample_rate * settings.window_seconds:
                raise ValueError('Training clips must fit in one window')
            variants = perturb(audio, settings.sample_rate, int(digest[:8], 16))
            for condition in PLAN['augmentations']:
                captured.clear()
                engine.analyze(variants[condition])
                if len(captured) != 1:
                    raise ValueError('Expected one training window')
                features.append(captured[0][0].copy())
                labels.append(int(label == 0))
            print(f'Frozen features: {number}/{len(selected)}', flush=True)
        features = np.asarray(features)
        scaler = StandardScaler().fit(features)
        learner = LogisticRegression(C=PLAN['C'], solver='liblinear', max_iter=1000,
                                     class_weight='balanced', random_state=PLAN['seed'])
        learner.fit(scaler.transform(features), labels)
        weights = learner.coef_[0] / scaler.scale_
        bias = float(learner.intercept_[0] - np.dot(weights, scaler.mean_))
        head = {'format': 'voiceguard-linear-head-v1', 'model_id': BASELINE,
                'revision': BASELINE_REVISION, 'feature_size': len(weights),
                'fake_index': engine.detectors[0].fake_index, 'weights': weights.tolist(), 'bias': bias,
                'experimental': True, 'dataset': DATASET, 'dataset_revision': REVISION,
                'dataset_license': 'ODC-By-1.0', 'attribution': 'ArAD, DeepFake-Audio-Rangers',
                'protocol_sha256': sha(json.dumps(PLAN, sort_keys=True).encode()),
                'training_selection_sha256': sha(json.dumps(selection, sort_keys=True).encode()),
                'training_clips': len(selected), 'training_variants': len(features),
                'limitations': PLAN['limitations']}
        (out / 'arabic_head.json').write_text(json.dumps(head, indent=2, allow_nan=False) + '\n')
        np.savez_compressed(out / 'training-features.npz', features=features, labels=np.asarray(labels))
        evaluate_rows = dev_rows
    else:
        fit = json.loads((out / 'fit.json').read_text())
        head_bytes = (out / 'arabic_head.json').read_bytes()
        if sha(head_bytes) != fit['head_sha256']:
            p.error('Head changed after development; confirmation prohibited')
        head = json.loads(head_bytes)
        weights, bias = np.asarray(head['weights']), head['bias']
        pool = [r for r in test_rows if sha(r['audio']['bytes']) not in reviewed]
        # Same untouched confirmation selection as the earlier comparison protocol.
        selected, duplicates = select_rows(pool, PLAN['confirmation_per_class'], 20261021)
        evaluate_rows = [pool[index] for index, _, _ in selected]
        train_hashes = {r['sha256'] for r in json.loads((out / 'train-selection.json').read_text())}
        if any(sha(r['audio']['bytes']) in reviewed | dev_hashes | train_hashes for r in evaluate_rows):
            p.error('Confirmation selection overlaps with training, development or reviewed clips')
    frozen = [{'sha256': sha(r['audio']['bytes']), 'label': int(r['label'] == 0)} for r in evaluate_rows]
    (out / f'{args.stage}-selection.json').write_text(json.dumps(frozen, indent=2) + '\n')
    samples, robust_counts = [], {0: 0, 1: 0}
    for number, row in enumerate(evaluate_rows, 1):
        digest, label = sha(row['audio']['bytes']), int(row['label'] == 0)
        vector, baseline = extract(row)
        adapted = float(expit(np.dot(weights, vector) + bias))
        sample = {'sha256': digest, 'label': label, 'baseline': baseline, 'adapted': adapted}
        if args.stage == 'confirmation' and robust_counts[label] < PLAN['robustness_per_class']:
            robust_counts[label] += 1
            sample['robustness'] = {}
            variants = perturb(clip_audio(row, settings), settings.sample_rate, int(digest[:8], 16))
            for condition, changed in variants.items():
                captured.clear()
                original = engine.analyze(changed)['_raw_fake_score']
                changed_score = float(expit(np.dot(weights, captured[0][0]) + bias))
                sample['robustness'][condition] = {'baseline': original, 'adapted': changed_score}
        samples.append(sample)
        print(f'{args.stage} comparison: {number}/{len(evaluate_rows)}', flush=True)
    hook.remove()
    results = {name: metrics([s['label'] for s in samples], [s[name] for s in samples])
               for name in ['baseline', 'adapted']}
    robust = [s for s in samples if 'robustness' in s]
    robustness = {condition: {name: metrics([s['label'] for s in robust],
                                          [s['robustness'][condition][name] for s in robust])
                              for name in ['baseline', 'adapted']}
                  for condition in (robust[0]['robustness'] if robust else [])}
    passed = gains_pass(results['baseline'], results['adapted'])
    if robustness:
        passed = passed and all(v['adapted']['accuracy'] >= v['baseline']['accuracy']
                                for key, v in robustness.items() if key != 'original')
    # Verify the saved JSON runtime head agrees with offline linear predictions.
    engine.detectors[0].install_head(out / 'arabic_head.json', BASELINE, BASELINE_REVISION)
    for row, expected in zip(evaluate_rows[:4], samples[:4]):
        actual = engine.analyze(clip_audio(row, settings))['_raw_fake_score']
        if not np.isclose(actual, expected['adapted'], atol=2e-6):
            raise ValueError('Runtime head disagrees with offline adaptation')
    base_identity = engine.identity()
    adapted_identity = json.loads(json.dumps(base_identity))
    adapted_identity['models'][0]['head_sha256'] = sha((out / 'arabic_head.json').read_bytes())
    report = {'stage': args.stage, 'protocol': PLAN, 'sources': sources,
              'head_sha256': sha((out / 'arabic_head.json').read_bytes()),
              'base_identity': base_identity, 'adapted_identity': adapted_identity,
              'results': results, 'robustness': robustness,
              'criteria_passed': bool(passed), 'samples': samples,
              'note': 'Exploratory clip-disjoint public study. Unknown speaker overlap. Before speech gate/abstention.'}
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'criteria_passed': bool(passed), 'accuracy': {k: v['accuracy'] for k, v in results.items()}}, indent=2))


if __name__ == '__main__':
    main()
