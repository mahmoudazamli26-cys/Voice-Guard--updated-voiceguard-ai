"""Prepare public test clips, then evaluate USER-MADE physical re-recordings.

No source speaker consent is invented. Playback uses publisher-licensed ArAD;
evaluation requires permission for new recordings and attestation of real capture.
Phone recordings stay local. Never substitute digitally altered clips for capture.
"""
import argparse
import hashlib
import html
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import requests
from scipy.signal import correlate
import soundfile as sf

from voiceguard.audio import decode_audio
from voiceguard.config import Settings
from voiceguard.engine import Engine
from voiceguard.metrics import metrics, decision_metrics
from voiceguard.speech import SpeechDetector

ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / 'voiceguard/assets/physical_plan.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_wave(data, clip):
    info = sf.info(io.BytesIO(data))
    if info.samplerate != clip['sample_rate'] or info.frames != clip['frames'] or info.channels != clip['channels']:
        raise ValueError('Downloaded waveform does not match the frozen public clip')
    audio, rate = sf.read(io.BytesIO(data), dtype='float32', always_2d=True)
    if (rate != clip['sample_rate'] or audio.shape != (clip['frames'], clip['channels'])
            or sha(audio.astype('<f4').tobytes()) != clip['pcm_sha256']):
        raise ValueError('Downloaded waveform does not match the frozen public clip')
    return audio.mean(axis=1)


def download_clip(plan, clip):
    response = requests.get('https://datasets-server.huggingface.co/rows', params={
        'dataset': plan['dataset'], 'config': 'default', 'split': 'test',
        'offset': clip['row_index'], 'length': 1}, timeout=30)
    response.raise_for_status()
    row = response.json()['rows'][0]
    if row['row_idx'] != clip['row_index'] or int(row['row']['label'] == 0) != clip['label']:
        raise ValueError('Publisher row or label differs from the frozen plan')
    url = row['row']['audio'][0]['src']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'datasets-server.huggingface.co' or plan['revision'] not in parsed.path:
        raise ValueError('Dataset revision or public audio host changed; do not silently substitute clips')
    with requests.get(url, timeout=30, stream=True) as audio_response:
        audio_response.raise_for_status()
        chunks, length = [], 0
        for chunk in audio_response.iter_content(65536):
            length += len(chunk)
            if length > 2 * 1024 * 1024:
                raise ValueError('Public audio exceeded the expected size')
            chunks.append(chunk)
    data = b''.join(chunks)
    verify_wave(data, clip)
    return data


def prepare(folder, plan):
    (folder / 'originals').mkdir(parents=True, exist_ok=True)
    (folder / 'recordings').mkdir(exist_ok=True)
    entries = []
    for clip in plan['clips']:
        name = clip['sample_id']
        path = folder / 'originals' / (name + '.wav')
        if path.exists():
            verify_wave(path.read_bytes(), clip)
        else:
            path.write_bytes(download_clip(plan, clip))
        entries.append(f'<li><h2>{html.escape(name)}</h2><audio controls preload="none" '
                       f'src="originals/{name}.wav"></audio><p>Save your phone recording as '
                       f'<strong>{name}.m4a</strong> (or .wav) inside the recordings folder.</p></li>')
        print('Ready: ' + name, flush=True)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VoiceGuard physical playback test</title><style>body{font:18px/1.6 system-ui;max-width:760px;margin:30px auto;padding:16px}li{padding:14px;border-bottom:1px solid #aaa}audio{width:100%}</style>
<h1>Physical speaker/microphone test</h1><p>Use a quiet room. Keep the phone about 50 cm from the laptop speaker and keep volume/distance constant. Record each sample separately, without speaking over it. Begin recording before playback and stop afterward.</p>
<p>Use a REAL speaker and microphone. Copying audio files or adding digital noise does not count as physical capture. Avoid recording bystanders. Do not change the supplied originals.</p>
<ol>''' + ''.join(entries) + '''</ol><p>Source: ArAD / DeepFake-Audio-Rangers, stated ODC-By-1.0 license. Source speaker consent is unverified. These public research clips are not proof of real-world detection performance.</p></html>'''
    (folder / 'play_samples.html').write_text(page, encoding='utf-8')
    (folder / 'source-plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print('Open: ' + str(folder / 'play_samples.html'), flush=True)


def align_recording(original, recorded):
    """Match content by normalized correlation, never by detector score.

    Crop to original duration so phone lead-in/trailing silence does not change
    window counts. Return alignment diagnostics; poor matches fail visibly.
    """
    original = np.asarray(original, dtype=np.float64)
    recorded = np.asarray(recorded, dtype=np.float64)
    if original.ndim != 1 or recorded.ndim != 1 or not np.isfinite(original).all() or not np.isfinite(recorded).all():
        raise ValueError('Alignment needs finite mono samples')
    if not len(original) or len(recorded) < len(original):
        raise ValueError('Phone recording is shorter than the complete original clip')
    template = original - original.mean()
    energy = float(np.dot(template, template))
    if energy < 1e-10:
        raise ValueError('Original has no usable alignment signal')
    length = len(template)
    cumulative = np.r_[0., np.cumsum(recorded)]
    squared = np.r_[0., np.cumsum(recorded ** 2)]
    sums = cumulative[length:] - cumulative[:-length]
    windows = squared[length:] - squared[:-length] - sums ** 2 / length
    norm = np.sqrt(np.maximum(windows, 1e-12) * energy)
    values = correlate(recorded, template, mode='valid', method='fft') / norm
    start = int(np.argmax(np.abs(values)))
    similarity = float(min(1., abs(values[start])))
    if similarity < .05:
        raise ValueError('Could not match the played clip; check sample names and re-record the full clip')
    return recorded[start:start + length].astype(np.float32), start, similarity


def evaluate(folder, plan, report_name='physical-report.json'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.json', report_name):
        raise ValueError('Report name must be a simple JSON filename')
    if report_name != 'physical-report.json' and (folder / report_name).exists():
        raise ValueError('Preserve the previous candidate report before rerunning')
    allowed = {'.wav', '.m4a', '.mp3', '.webm', '.ogg', '.flac'}
    # Fail before loading the large model when phone files have not been supplied.
    for clip in plan['clips']:
        name = clip['sample_id']
        candidates = [p for p in (folder / 'recordings').glob(name + '.*') if p.suffix.lower() in allowed]
        if not (folder / 'originals' / (name + '.wav')).is_file() or len(candidates) != 1:
            raise ValueError('Prepare the clips and provide exactly one real phone recording for ' + name)
    # Settings may download the public model if uncached; recordings are never sent.
    settings = Settings.from_env()
    engine, speech = Engine(settings), SpeechDetector()
    pairs = []
    for clip in plan['clips']:
        name = clip['sample_id']
        original_bytes = (folder / 'originals' / (name + '.wav')).read_bytes()
        verify_wave(original_bytes, clip)
        candidates = [p for p in (folder / 'recordings').glob(name + '.*') if p.suffix.lower() in allowed]
        if len(candidates) != 1:
            raise ValueError('Need exactly one phone recording for ' + name)
        source = candidates[0]
        if source.stat().st_size > settings.max_bytes:
            raise ValueError('Phone recording exceeds upload size limit: ' + name)
        new_bytes = source.read_bytes()
        original = decode_audio(original_bytes, settings.sample_rate, settings.max_seconds)
        recorded = decode_audio(new_bytes, settings.sample_rate, settings.max_seconds)
        aligned, offset, similarity = align_recording(original, recorded)
        scores, eligibility, decisions = {}, {}, {}
        for condition, audio in [('original', original), ('loudspeaker_rerecorded', aligned)]:
            eligible = speech.contains_speech(audio, settings.sample_rate)
            analysis = engine.analyze(audio)
            scores[condition], eligibility[condition] = analysis['_raw_fake_score'], eligible
            decisions[condition] = analysis['prediction'] if eligible else 'inconclusive'
        pairs.append({'sample_id': name, 'label': clip['label'], 'scores': scores,
                      'speech_detected': eligibility, 'decisions': decisions,
                      'original_sha256': sha(original_bytes), 'phone_file_sha256': sha(new_bytes),
                      'phone_duration_seconds': len(recorded) / settings.sample_rate,
                      'compared_duration_seconds': len(aligned) / settings.sample_rate,
                      'alignment_offset_seconds': offset / settings.sample_rate,
                      'alignment_correlation': similarity})
        print('Evaluated: ' + name, flush=True)
    conditions = {}
    for condition in ['original', 'loudspeaker_rerecorded']:
        labels, scores = [p['label'] for p in pairs], [p['scores'][condition] for p in pairs]
        conditions[condition] = {'raw_metrics': metrics(labels, scores)}
        if engine.calibration:
            conditions[condition]['calibrated_decisions'] = decision_metrics(labels, scores, engine.calibration,
                [p['speech_detected'][condition] for p in pairs])
    changes = [p['scores']['loudspeaker_rerecorded'] - p['scores']['original'] for p in pairs]
    report = {'physical_capture': 'user-attested; not independently verified',
              'recording_permission': 'user-confirmed for newly captured files',
              'source_speaker_consent': 'unverified', 'source_license': plan['license'],
              'source_dataset': plan['dataset'], 'source_revision': plan['revision'],
              'identity': engine.identity(), 'calibration_applied': engine.calibration is not None,
              'conditions': conditions, 'pairs': pairs,
              'mean_absolute_score_change': float(np.mean(np.abs(changes))),
              'mean_signed_score_change': float(np.mean(changes)),
              'note': f'{len(pairs)} public pairs; unknown speaker independence. Raw classifier metrics precede the speech gate. No claim for other devices/rooms.'}
    path = folder / report_name
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('Report saved locally: ' + str(path), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['prepare', 'evaluate'])
    p.add_argument('--folder', default='physical-test')
    p.add_argument('--confirm-recording-permission', action='store_true')
    p.add_argument('--confirm-physical-capture', action='store_true')
    p.add_argument('--report-name', default='physical-report.json', help='Separate JSON filename for candidate comparisons')
    args = p.parse_args()
    if args.stage == 'evaluate' and not (args.confirm_recording_permission and args.confirm_physical_capture):
        p.error('Evaluation requires permission for your recordings AND actual speaker/microphone capture')
    plan = json.loads(PLAN_PATH.read_text())
    folder = Path(args.folder).resolve()
    if args.stage == 'prepare':
        prepare(folder, plan)
    else:
        evaluate(folder, plan, args.report_name)


if __name__ == '__main__':
    main()
