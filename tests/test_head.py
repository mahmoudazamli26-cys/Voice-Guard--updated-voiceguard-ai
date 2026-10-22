from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from scipy.special import expit

from voiceguard.config import Settings
from voiceguard.engine import Detector, Engine
from voiceguard.head import read_head


def artifact(tmp_path, **updates):
    data = {'format': 'voiceguard-linear-head-v1', 'model_id': 'test', 'revision': 'pinned',
            'feature_size': 3, 'fake_index': 1, 'weights': [1., -2., .5], 'bias': .25}
    data.update(updates)
    path = tmp_path / 'head.json'
    path.write_text(json.dumps(data))
    return path


def detector():
    item = Detector.__new__(Detector)
    item.torch, item.fake_index = torch, 1
    item.model = SimpleNamespace(classifier=torch.nn.Linear(3, 2))
    return item


def test_saved_head_preserves_logistic_score(tmp_path):
    path = artifact(tmp_path)
    item = detector()
    item.install_head(path, 'test', 'pinned')
    vectors = np.array([[0, 1, 2], [1, -1, .5]], dtype=np.float32)
    expected = expit(vectors @ np.array([1., -2., .5]) + .25)
    actual = torch.softmax(item.model.classifier(torch.from_numpy(vectors)), dim=-1)[:, 1]
    assert actual.detach().numpy() == pytest.approx(expected, abs=1e-7)
    assert item.head_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('updates', [
    {'model_id': 'other'}, {'revision': 'other'}, {'fake_index': 0},
    {'feature_size': 4}, {'weights': [1, 2]}, {'weights': [float('nan'), 2, 3]},
    {'bias': float('inf')}, {'weights': [1e8, 2, 3]},
])
def test_invalid_or_mismatched_head_rejected(tmp_path, updates):
    with pytest.raises(ValueError):
        read_head(artifact(tmp_path, **updates), 'test', 'pinned', 3, 1)


def test_head_change_invalidates_previous_calibration(tmp_path):
    path = artifact(tmp_path)
    settings = replace(Settings(), model_id='test', revision='pinned', head_path=str(path))
    engine = Engine(settings, [detector()])
    calibration = tmp_path / 'calibration.json'
    calibration.write_text(json.dumps({'identity': engine.identity(), 'real_threshold': .2, 'fake_threshold': .8}))
    artifact(tmp_path, bias=1.)
    with pytest.raises(ValueError, match='does not match'):
        Engine(replace(settings, calibration=str(calibration)), [detector()])


def test_profile_is_opt_in_and_invalid_names_fail(monkeypatch):
    monkeypatch.delenv('VG_HEAD_PATH', raising=False)
    monkeypatch.setenv('VG_PROFILE', 'base')
    assert Settings.from_env().head_path == ''
    monkeypatch.setenv('VG_PROFILE', 'experimental-arabic')
    assert Settings.from_env().head_path.endswith('assets/arabic_head.json')
    monkeypatch.setenv('VG_HEAD_PATH', '')
    assert Settings.from_env().head_path.endswith('assets/arabic_head.json')
    monkeypatch.delenv('VG_CALIBRATION', raising=False)
    monkeypatch.setenv('VG_PROFILE', 'experimental-arabic-calibrated')
    assert Settings.from_env().calibration.endswith('assets/arabic_calibration.json')
    monkeypatch.setenv('VG_PROFILE', 'unknown')
    with pytest.raises(ValueError, match='VG_PROFILE'):
        Settings.from_env()
