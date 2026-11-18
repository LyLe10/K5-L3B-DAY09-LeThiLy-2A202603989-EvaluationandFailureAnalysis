"""Edge cases for M2 judge calibration statistics."""

import pytest

from lab9 import stats


def test_confusion_counts_fail_as_positive():
    assert stats.confusion(["FAIL", "PASS", "FAIL", "PASS"],
                           ["FAIL", "FAIL", "PASS", "PASS"]) == {
                               "tp": 1, "fp": 1, "fn": 1, "tn": 1}


def test_confusion_rejects_unpaired_or_invalid_labels():
    with pytest.raises(ValueError):
        stats.confusion(["FAIL"], [])
    with pytest.raises(ValueError):
        stats.confusion(["unknown"], ["PASS"])


def test_precision_recall_zero_denominators():
    assert stats.precision_recall(["PASS"], ["PASS"]) == (0.0, 0.0)
    assert stats.precision_recall(["FAIL"], ["PASS"]) == (0.0, 0.0)
    assert stats.precision_recall(["PASS"], ["FAIL"]) == (0.0, 0.0)


def test_kappa_edge_cases():
    with pytest.raises(ValueError):
        stats.cohen_kappa([], [])
    with pytest.raises(ValueError):
        stats.cohen_kappa(["FAIL"], ["FAIL"])
    assert stats.cohen_kappa(["FAIL", "PASS"], ["PASS", "FAIL"]) == -1.0
    assert stats.cohen_kappa(["FAIL", "PASS"], ["FAIL", "PASS"]) == 1.0


def test_rogan_gladen_undefined_and_clipping():
    with pytest.raises(ValueError):
        stats.rogan_gladen(0.2, 0.5, 0.5)
    assert stats.rogan_gladen(0.0, 0.8, 0.9) == 0.0
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
    assert stats.rogan_gladen(0.28, 0.8, 66 / 70) == pytest.approx(0.3)
