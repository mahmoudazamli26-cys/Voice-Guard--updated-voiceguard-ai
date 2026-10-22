"""Consent-aware labeled manifests with speaker-disjoint partitions."""
import csv
import hashlib
from pathlib import Path
from voiceguard.audio import decode_audio


def read_manifest(filename):
    path = Path(filename).resolve()
    rows = list(csv.DictReader(path.open(newline='', encoding='utf-8')))
    if not rows:
        raise ValueError('Manifest has no recordings')
    required = {'path','label','speaker','language','split','consent'}
    if not required.issubset(rows[0]):
        raise ValueError('Manifest requires path,label,speaker,language,split,consent')
    speakers, identities = {}, {}
    for row in rows:
        if row['label'] not in {'real','fake'} or row['split'] not in {'train','validation','test'}:
            raise ValueError('Invalid label or split')
        if row['consent'].lower() != 'true' or not row['speaker'] or not row['language']:
            raise ValueError('Every row needs consent, a speaker group, and language')
        group = row['speaker']
        if group in speakers and speakers[group] != row['split']:
            raise ValueError('Speaker leakage between dataset splits')
        speakers[group] = row['split']
        audio_path = (path.parent / row['path']).resolve()
        if not audio_path.is_file():
            raise ValueError('An audio file in the manifest is missing')
        row['resolved_path'] = audio_path
        digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        if digest in identities:
            raise ValueError('Duplicate recording content; remove duplicates before evaluation')
        identities[digest] = row['split']
        row['id'] = digest
    return rows


def load_audio(row, settings):
    path = row['resolved_path']
    if path.stat().st_size > settings.max_bytes:
        raise ValueError('Dataset recording exceeds the configured upload size limit')
    return decode_audio(path.read_bytes(), settings.sample_rate, settings.max_seconds)
