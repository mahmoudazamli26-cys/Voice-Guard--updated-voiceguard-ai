"""Load a local linear adaptation as finite JSON data, never executable weights."""
import hashlib
import json
from pathlib import Path

import numpy as np


def read_head(path, model_id, revision, feature_size, fake_index):
    source = Path(path)
    if source.stat().st_size > 128 * 1024:
        raise ValueError('Adaptation file is too large')
    raw = source.read_bytes()
    data = json.loads(raw)
    expected = {'format': 'voiceguard-linear-head-v1', 'model_id': model_id,
                'revision': revision, 'feature_size': feature_size, 'fake_index': fake_index}
    if any(data.get(key) != value for key, value in expected.items()):
        raise ValueError('Adaptation does not match the pinned model and label mapping')
    weights = np.asarray(data['weights'], dtype=np.float64)
    bias = float(data['bias'])
    if weights.shape != (feature_size,) or not np.isfinite(weights).all() or not np.isfinite(bias):
        raise ValueError('Adaptation weights must have the expected shape and be finite')
    if np.max(np.abs(weights)) > 1e6 or abs(bias) > 1e6:
        raise ValueError('Adaptation weights exceed supported bounds')
    return weights, bias, hashlib.sha256(raw).hexdigest()
