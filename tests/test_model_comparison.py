from compare_arabic_models import gains_pass
from voiceguard.metrics import metrics


def test_improvement_requires_both_classes_not_just_fake_recall():
    labels = [0] * 100 + [1] * 100
    baseline = metrics(labels, [.1] * 90 + [.9] * 10 + [.1] * 50 + [.9] * 50)
    all_fake = metrics(labels, [.9] * 200)
    assert not gains_pass(baseline, all_fake)
    candidate = metrics(labels, [.1] * 90 + [.9] * 10 + [.1] * 20 + [.9] * 80)
    assert gains_pass(baseline, candidate)


def test_small_gain_does_not_pass_frozen_criteria():
    labels = [0] * 100 + [1] * 100
    baseline = metrics(labels, [.1] * 90 + [.9] * 10 + [.1] * 50 + [.9] * 50)
    candidate = metrics(labels, [.1] * 90 + [.9] * 10 + [.1] * 48 + [.9] * 52)
    assert not gains_pass(baseline, candidate)
