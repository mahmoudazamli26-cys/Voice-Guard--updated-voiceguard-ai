import hashlib
import pytest
from public_arabic_benchmark import select_rows


def row(value, label):
    return {'audio': {'bytes': value}, 'label': label}


def test_sampling_balanced_reproducible_and_deduplicated():
    rows = [row(str(i).encode(), i % 2) for i in range(20)]
    rows.append(rows[0])
    selected, duplicates = select_rows(rows, 4, 42)
    assert duplicates == 1
    assert selected == select_rows(rows, 4, 42)[0]
    assert [label for _, label, _ in selected].count(0) == 4
    assert [label for _, label, _ in selected].count(1) == 4
    assert len({digest for _, _, digest in selected}) == 8
    assert all(digest == hashlib.sha256(rows[i]['audio']['bytes']).hexdigest()
               for i, _, digest in selected)


def test_conflicting_duplicate_labels_fail():
    with pytest.raises(ValueError, match='Conflicting'):
        select_rows([row(b'same', 0), row(b'same', 1)], 1, 42)


def test_insufficient_class_fails():
    with pytest.raises(ValueError, match='Not enough'):
        select_rows([row(b'one', 0)], 2, 42)
