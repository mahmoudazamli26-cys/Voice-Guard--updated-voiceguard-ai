"""Fit experimental thresholds on new public validation clips, then test once.

No speaker-independence or individual-consent claim is made for public ArAD.
Private, consented manifests remain a separate workflow.
"""
import argparse
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from compare_arabic_models import BASELINE, BASELINE_REVISION, clip_audio
from public_arabic_benchmark import DATASET, REVISION, FILE, select_rows
from robustness import perturb
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import calibrate, metrics, decision_metrics
from voiceguard.speech import SpeechDetector

ROOT = Path(__file__).resolve().parent
PLAN = {'version': 1, 'validation_per_class': 64, 'test_per_class': 128,
        'validation_seed': 20261023, 'test_seed': 20261024, 'physical_seed': 20261025,
        'physical_per_class': 4, 'robustness_per_class': 8,
        'max_validation_class_error': .02, 'max_test_class_error': .05,
        'minimum_test_coverage': .10, 'dataset': DATASET, 'revision': REVISION,
        'limitation': 'Experimental public clip-level calibration; speaker IDs and individual consent unavailable.'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def source_path(filename):
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(DATASET, filename, revision=REVISION, repo_type='dataset'))


def published_rows(filename):
    import pyarrow.parquet as pq
    rows = pq.read_table(source_path(filename)).to_pylist()
    for index, row in enumerate(rows):
        row['_source'], row['_row'] = filename, index
    return rows


def selected_metadata(pool, count, seed):
    selected, _ = select_rows(pool, count, seed)
    return [{'source_file': pool[i]['_source'], 'row_index': pool[i]['_row'],
             'sha256': digest, 'label': int(label == 0)} for i, label, digest in selected]


def selected_audio(selection):
    by_source = {}
    for item in selection:
        by_source.setdefault(item['source_file'], []).append(item)
    result = {}
    for filename, items in by_source.items():
        rows = published_rows(filename)
        for item in items:
            row = rows[item['row_index']]
            if sha(row['audio']['bytes']) != item['sha256'] or int(row['label'] == 0) != item['label']:
                raise ValueError('Pinned source audio or labels do not match the frozen selection')
            result[item['sha256']] = row
    return [result[item['sha256']] for item in selection]


def prepare(out):
    test = published_rows(FILE)
    test_hashes = {sha(r['audio']['bytes']) for r in test}
    training = []
    sources = []
    for number in range(3):
        filename = f'data/train-{number:05d}-of-00003.parquet'
        training.extend(published_rows(filename))
        sources.append({'file': filename, 'sha256': sha(source_path(filename).read_bytes())})
    sources.append({'file': FILE, 'sha256': sha(source_path(FILE).read_bytes())})
    head_root = ROOT / 'docs/results/model-improvement/head'
    used_training = set()
    for name in ['train-selection.json', 'fit-selection.json']:
        used_training.update(s['sha256'] for s in json.loads((head_root / name).read_text()))
    reviewed = {s['sha256'] for s in json.loads((ROOT / 'docs/results/arad-base.json').read_text())['samples']}
    reviewed.update(s['sha256'] for s in json.loads((head_root / 'confirmation-selection.json').read_text()))
    validation_pool = [r for r in training if sha(r['audio']['bytes']) not in used_training | test_hashes]
    validation = selected_metadata(validation_pool, PLAN['validation_per_class'], PLAN['validation_seed'])
    test_pool = [r for r in test if sha(r['audio']['bytes']) not in reviewed]
    testing = selected_metadata(test_pool, PLAN['test_per_class'], PLAN['test_seed'])
    excluded = reviewed | {s['sha256'] for s in testing}
    physical_pool = [r for r in test if sha(r['audio']['bytes']) not in excluded
                     and sf.info(io.BytesIO(r['audio']['bytes'])).duration >= 2]
    physical = selected_metadata(physical_pool, PLAN['physical_per_class'], PLAN['physical_seed'])
    rows = selected_audio(physical)
    # Only duration, random seed and labels select clips; detector scores do not.
    rng = np.random.default_rng(PLAN['physical_seed'])
    order = rng.permutation(len(physical))
    clips = []
    for number, index in enumerate(order, 1):
        row, metadata = rows[int(index)], physical[int(index)]
        audio, rate = sf.read(io.BytesIO(row['audio']['bytes']), dtype='float32', always_2d=True)
        clips.append({**metadata, 'sample_id': f'sample_{number:02d}', 'sample_rate': rate,
                      'frames': len(audio), 'channels': audio.shape[1],
                      'pcm_sha256': sha(audio.astype('<f4').tobytes())})
    save(out / 'selection.json', {'protocol': PLAN, 'sources': sources, 'validation': validation,
                                  'test': testing, 'physical': clips,
                                  'head_sha256': sha((ROOT / 'voiceguard/assets/arabic_head.json').read_bytes())})
    save(out / 'physical_plan.json', {'dataset': DATASET, 'revision': REVISION,
                                     'license': 'ODC-By-1.0', 'source_speaker_consent': 'unverified',
                                     'attribution': 'ArAD / DeepFake-Audio-Rangers', 'clips': clips})
    print('Frozen selections: 128 validation, 256 new test, 8 physical-test clips', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['prepare', 'calibrate', 'test'], required=True)
    p.add_argument('--output-dir', default='reports/public-calibration')
    args = p.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    final_file = out / ('selection.json' if args.stage == 'prepare' else args.stage + '.json')
    if final_file.exists():
        p.error('Preserve completed stages; use a new directory instead of overwriting')
    if args.stage == 'prepare':
        prepare(out)
        return
    selection = json.loads((out / 'selection.json').read_text())
    if selection['protocol'] != PLAN:
        p.error('Protocol differs from the frozen selection')
    head = ROOT / 'voiceguard/assets/arabic_head.json'
    if sha(head.read_bytes()) != selection['head_sha256']:
        p.error('Head changed after selection')
    settings = replace(Settings(), model_id=BASELINE, revision=BASELINE_REVISION,
                       head_path=str(head), cpu_threads=4)
    if args.stage == 'test':
        previous = json.loads((out / 'calibrate.json').read_text())
        if sha((out / 'calibration.json').read_bytes()) != previous['calibration_sha256']:
            p.error('Thresholds changed after validation')
        settings = replace(settings, calibration=str(out / 'calibration.json'))
    engine, speech = Engine(settings), SpeechDetector()
    chosen = selection['validation' if args.stage == 'calibrate' else 'test']
    samples = []
    robust_counts = {0: 0, 1: 0}
    for number, (metadata, row) in enumerate(zip(chosen, selected_audio(chosen)), 1):
        audio = clip_audio(row, settings)
        has_speech = speech.contains_speech(audio, settings.sample_rate)
        analysis = engine.analyze(audio)
        sample = {**metadata, 'speech_detected': has_speech,
                  'score': analysis['_raw_fake_score'],
                  'decision': analysis['prediction'] if has_speech else 'inconclusive'}
        if args.stage == 'test' and robust_counts[metadata['label']] < PLAN['robustness_per_class']:
            robust_counts[metadata['label']] += 1
            sample['robustness'] = {}
            for condition, changed in perturb(audio, settings.sample_rate, int(metadata['sha256'][:8], 16)).items():
                scored = engine.analyze(changed)
                sample['robustness'][condition] = {'score': scored['_raw_fake_score'],
                    'speech_detected': speech.contains_speech(changed, settings.sample_rate)}
        samples.append(sample)
        print(f'{args.stage}: {number}/{len(chosen)}', flush=True)
    report = {'protocol': PLAN, 'identity': engine.identity(), 'samples': samples,
              'raw_classifier_metrics': metrics([s['label'] for s in samples], [s['score'] for s in samples]),
              'scope': 'Experimental public byte-disjoint clips; unknown speaker and pretrained-data overlap.'}
    if args.stage == 'calibrate':
        validation = [s for s in samples if s['speech_detected']]
        calibration = calibrate([s['label'] for s in validation], [s['score'] for s in validation],
                                max_error=PLAN['max_validation_class_error'])
        calibration.update(identity=engine.identity(), split='validation', experimental=True,
                           dataset=DATASET, dataset_revision=REVISION,
                           dataset_sha256=sha(json.dumps(chosen, sort_keys=True).encode()),
                           scope=report['scope'])
        save(out / 'calibration.json', calibration)
        for sample in samples:
            sample['decision'] = ('inconclusive' if not sample['speech_detected'] else
                'real' if sample['score'] <= calibration['real_threshold'] else
                'fake' if sample['score'] >= calibration['fake_threshold'] else 'inconclusive')
        report['calibration_sha256'] = sha((out / 'calibration.json').read_bytes())
        report['decisions'] = decision_metrics([s['label'] for s in samples], [s['score'] for s in samples],
                                               calibration, [s['speech_detected'] for s in samples])
    else:
        calibration = engine.calibration
        report['calibration_sha256'] = sha((out / 'calibration.json').read_bytes())
        report['decisions'] = decision_metrics([s['label'] for s in samples], [s['score'] for s in samples],
                                               calibration, [s['speech_detected'] for s in samples])
        robust = [s for s in samples if 'robustness' in s]
        report['robustness'] = {condition: {
            'raw_metrics': metrics([s['label'] for s in robust], [s['robustness'][condition]['score'] for s in robust]),
            'decisions': decision_metrics([s['label'] for s in robust],
                [s['robustness'][condition]['score'] for s in robust], calibration,
                [s['robustness'][condition]['speech_detected'] for s in robust])}
            for condition in robust[0]['robustness']}
        d = report['decisions']
        report['experimental_check_passed'] = (d['coverage'] >= PLAN['minimum_test_coverage'] and
            max(d['false_real_rate'], d['false_fake_rate']) <= PLAN['max_test_class_error'])
    save(final_file, report)
    print(json.dumps(report['decisions'], indent=2), flush=True)


if __name__ == '__main__':
    main()
