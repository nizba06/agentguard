"""Tests for shared injection scoring helpers."""

from __future__ import annotations

import numpy as np
import pytest

from training.scoring import (
    injection_probability,
    resolve_injection_class_index,
    softmax,
    validate_probe,
)


def test_softmax_prefers_higher_logit() -> None:
    probs = softmax(np.array([[0.0, 2.0]], dtype=np.float32))
    assert probs[0, 1] > probs[0, 0]


def test_resolve_injection_class_index_prefers_discriminative_column() -> None:
    inj = np.array([[2.0, -2.0], [1.5, -1.0]], dtype=np.float32)
    ben = np.array([[-2.0, 2.0], [-1.5, 1.0]], dtype=np.float32)
    assert resolve_injection_class_index(inj, ben, preferred_index=1) == 0

    inj_swapped = np.array([[-2.0, 2.0], [-1.5, 1.5]], dtype=np.float32)
    ben_swapped = np.array([[2.0, -2.0], [1.5, -1.5]], dtype=np.float32)
    assert resolve_injection_class_index(inj_swapped, ben_swapped, preferred_index=0) == 1


def test_resolve_falls_back_to_preferred_when_gap_tiny() -> None:
    # Near-identical logits — old resolver flipped to index 1 and reported collapse.
    inj = np.array([[4.15, -5.14]], dtype=np.float32)
    ben = np.array([[4.17, -5.20]], dtype=np.float32)
    assert resolve_injection_class_index(inj, ben, preferred_index=1) == 1


def test_injection_probability_uses_selected_index() -> None:
    logits = np.array([4.0, -4.0], dtype=np.float32)
    assert injection_probability(logits, 0) > 0.9
    assert injection_probability(logits, 1) < 0.1


def test_validate_probe_rejects_collapsed_scores() -> None:
    with pytest.raises(RuntimeError, match="collapsed"):
        validate_probe(0.01, 0.01, min_gap=0.3, context="test")


def test_validate_probe_rejects_wrong_direction() -> None:
    with pytest.raises(RuntimeError, match="failed probe"):
        validate_probe(0.2, 0.8, min_gap=0.3, context="test")
