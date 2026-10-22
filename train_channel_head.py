"""Frozen-encoder channel augmentation experiment; no physical robustness claim.

Uses public publisher-licensed ArAD clips. Individual consent and speaker IDs
are unavailable. Previous tests and eight phone-test source clips are excluded
from fitting/development; confirmation clips exclude all reviewed test clips.
The application head and calibration are never replaced by this script.
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

from calibrate_public_arabic import published_rows, selected_audio, selected_metadata, sha, save
from compare_arabic_models import BASELINE, BASELINE_REVISION, clip_audio
from public_arabic_benchmark import DATASET, REVISION, FILE
from voiceguard.channel import simulated_playback
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import metrics

ROOT = Path(__file__).resolve().parent
PLAN = {'version': 1, 'seed': 20261026, 'test_per_class': 64, 'C': .1,
        'conditions': ['original', 'simulated_mild', 'simulated_strong'],
        'selection': 'Existing 256 training and 64 development clips; fresh 128 confirmation clips.',
        'development_rule': 'Both simulated accuracies improve at least 0.05; clean drops at most 0.03.',
        'confirmation_rule': 'Same accuracy rule plus fake recall must not fall for either channel.',
        'deployment': 'Never automatic: requires separate real playback validation and fresh physical test.',
        'dataset': DATASET, 'revision': REVISION,
        'limitation': 'Synthetic randomized channels, not measured room responses; unknown speaker independence.'}


def prepare(out):
    base = ROOT / 'docs/results/model-improvement/head'
    training = json.loads((base / 'train-selection.json').read_text())
    development = json.loads((base / 'fit-selection.json').read_text())
    used = {s['sha256'] for s in training + development}
    frozen = json.loads((ROOT / 'docs/results/calibration/selection.json').read_text())
    reserved = {s['sha256'] for k in ['validation', 'test', 'physical'] for s in frozen[k]}
    if used & reserved:
        raise ValueError('Training/development overlaps the reserved calibration/test/physical sources')
    rows = []
    for i in range(3):
        rows.extend(published_rows(f'data/train-{i:05d}-of-00003.parquet'))
    def locate(selection):
        labels = {s['sha256']: s['label'] for s in selection}
        found = {}
        for row in rows:
            digest = sha(row['audio']['bytes'])
            if digest in labels:
                if int(row['label'] == 0) != labels[digest]:
                    raise ValueError('Publisher label changed')
                found[digest] = {'source_file': row['_source'], 'row_index': row['_row'],
                                 'sha256': digest, 'label': labels[digest]}
        if set(found) != set(labels):
            raise ValueError('Training/development source clip missing')
        return [found[s['sha256']] for s in selection]
    test = published_rows(FILE)
    test_hashes = {sha(r['audio']['bytes']) for r in test}
    if used & test_hashes:
        raise ValueError('Publisher train/test byte overlap')
    reviewed = reserved | used
    for path in ['docs/results/arad-base.json', 'docs/results/model-improvement/head/confirmation-selection.json']:
        data = json.loads((ROOT / path).read_text())
        reviewed.update(s['sha256'] for s in (data['samples'] if isinstance(data, dict) else data))
    testing = selected_metadata([r for r in test if sha(r['audio']['bytes']) not in reviewed],
                                PLAN['test_per_class'], PLAN['seed'])
    save(out / 'selection.json', {'protocol': PLAN, 'train': locate(training),
                                  'development': locate(development), 'test': testing,
                                  'reference_head_sha256': sha((ROOT / 'voiceguard/assets/arabic_head.json').read_bytes()),
                                  'channel_code_sha256': sha((ROOT / 'voiceguard/channel.py').read_bytes())})


def score(weights, bias, vector):
    return float(expit(np.dot(weights, vector) + bias))


def passes(reference, candidate, confirmation=False):
    if candidate['original']['accuracy'] < reference['original']['accuracy'] - .03:
        return False
    for condition in PLAN['conditions'][1:]:
        if candidate[condition]['accuracy'] < reference[condition]['accuracy'] + .05:
            return False
        if confirmation and candidate[condition]['recall'] < reference[condition]['recall']:
            return False
    return True


def run(out, stage):
    selection = json.loads((out / 'selection.json').read_text())
    if selection['protocol'] != PLAN:
        raise ValueError('Frozen protocol differs')
    if selection['channel_code_sha256'] != sha((ROOT / 'voiceguard/channel.py').read_bytes()):
        raise ValueError('Channel simulation changed after selection')
    reference_path = ROOT / 'voiceguard/assets/arabic_head.json'
    if selection['reference_head_sha256'] != sha(reference_path.read_bytes()):
        raise ValueError('Reference classifier changed')
    reference = json.loads(reference_path.read_text())
    settings = replace(Settings(), cpu_threads=4)
    engine = Engine(settings)
    captured = []
    hook = engine.detectors[0].model.classifier.register_forward_pre_hook(
        lambda module, inputs: captured.append(inputs[0].detach().cpu().numpy().copy()))
    def features(audio):
        if len(audio) > settings.sample_rate * settings.window_seconds:
            raise ValueError('Only single-window source clips are supported')
        captured.clear()
        engine.analyze(audio)
        if len(captured) != 1 or captured[0].shape[0] != 1:
            raise ValueError('Expected one classifier input')
        return captured[0][0]
    def variants(audio, digest, split):
        seed = int(hashlib.sha256((digest + split).encode()).hexdigest()[:8], 16)
        return {'original': audio,
                'simulated_mild': simulated_playback(audio, settings.sample_rate, seed, 'mild'),
                'simulated_strong': simulated_playback(audio, settings.sample_rate, seed + 1, 'strong')}
    if stage == 'fit':
        x, y = [], []
        for i, (item, row) in enumerate(zip(selection['train'], selected_audio(selection['train'])), 1):
            for audio in variants(clip_audio(row, settings), item['sha256'], 'train').values():
                x.append(features(audio).copy()); y.append(item['label'])
            print(f'Training features {i}/256', flush=True)
        x = np.asarray(x)
        scaler = StandardScaler().fit(x)
        learner = LogisticRegression(C=PLAN['C'], solver='liblinear', max_iter=1000,
                                     class_weight='balanced', random_state=PLAN['seed']).fit(scaler.transform(x), y)
        weights = learner.coef_[0] / scaler.scale_
        bias = float(learner.intercept_[0] - np.dot(weights, scaler.mean_))
        candidate = {**reference, 'weights': weights.tolist(), 'bias': bias,
                     'training_variants': len(y), 'protocol_sha256': sha(json.dumps(PLAN, sort_keys=True).encode()),
                     'training_selection_sha256': sha(json.dumps(selection['train'], sort_keys=True).encode()),
                     'limitations': PLAN['limitation'], 'experimental': True}
        save(out / 'candidate_head.json', candidate)
        np.savez_compressed(out / 'features.npz', features=x, labels=y)
        subset = 'development'
    else:
        fit = json.loads((out / 'fit.json').read_text())
        if fit['selection_sha256'] != sha((out / 'selection.json').read_bytes()):
            raise ValueError('Selections changed after development')
        if not fit['criteria_passed']:
            raise ValueError('Development failed: preserve test as unopened')
        if fit['candidate_sha256'] != sha((out / 'candidate_head.json').read_bytes()):
            raise ValueError('Candidate changed after development')
        candidate = json.loads((out / 'candidate_head.json').read_text())
        weights, bias = np.asarray(candidate['weights']), candidate['bias']
        subset = 'test'
    samples = []
    for i, (item, row) in enumerate(zip(selection[subset], selected_audio(selection[subset])), 1):
        scores = {}
        for condition, audio in variants(clip_audio(row, settings), item['sha256'], subset).items():
            vector = features(audio)
            scores[condition] = {'reference': score(reference['weights'], reference['bias'], vector),
                                 'candidate': score(weights, bias, vector)}
        samples.append({**item, 'scores': scores})
        print(f'{subset} {i}/{len(selection[subset])}', flush=True)
    hook.remove()
    results = {name: {condition: metrics([s['label'] for s in samples],
                      [s['scores'][condition][name] for s in samples]) for condition in PLAN['conditions']}
               for name in ['reference', 'candidate']}
    passed = passes(results['reference'], results['candidate'], stage == 'confirmation')
    engine.detectors[0].install_head(out / 'candidate_head.json', BASELINE, BASELINE_REVISION)
    row = selected_audio(selection[subset][:1])[0]
    actual = engine.analyze(clip_audio(row, settings))['_raw_fake_score']
    if not np.isclose(actual, samples[0]['scores']['original']['candidate'], atol=2e-6):
        raise ValueError('Runtime head disagrees with offline candidate')
    save(out / (stage + '.json'), {'protocol': PLAN, 'selection_sha256': sha((out / 'selection.json').read_bytes()),
         'reference_sha256': selection['reference_head_sha256'],
         'candidate_sha256': sha((out / 'candidate_head.json').read_bytes()),
         'results': results, 'samples': samples, 'criteria_passed': bool(passed),
         'deployment_status': 'not installed; real playback validation and fresh physical testing required',
         'note': 'Raw 0.5 classifier diagnostics before speech gate; simulated channels, not physical capture.'})
    print(json.dumps({'criteria_passed': bool(passed), 'accuracy': {
        name: {k: v['accuracy'] for k, v in values.items()} for name, values in results.items()}}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', required=True, choices=['prepare', 'fit', 'confirmation'])
    p.add_argument('--output-dir', default='reports/channel-head')
    args = p.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    target = out / ('selection.json' if args.stage == 'prepare' else args.stage + '.json')
    if target.exists():
        p.error('Preserve completed results; use another output directory')
    if args.stage == 'prepare':
        prepare(out)
    else:
        run(out, args.stage)


if __name__ == '__main__':
    main()
