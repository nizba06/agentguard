"""Tests for ONNX export helpers."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from training.export_onnx import _extract_logits, _normalize_onnx_feed
from training.scoring import softmax


def test_softmax_binary() -> None:
    probs = softmax(np.array([[0.0, 2.0]], dtype=np.float32))
    assert probs.shape == (1, 2)
    assert probs[0, 1] > probs[0, 0]


def test_extract_logits_prefers_two_class_output() -> None:
    logits = np.array([[1.0, 3.0]], dtype=np.float32)
    hidden = np.zeros((1, 768), dtype=np.float32)
    extracted = _extract_logits([hidden, logits])
    np.testing.assert_array_equal(extracted, logits)


def test_normalize_onnx_feed_casts_int_inputs() -> None:
    session = SimpleNamespace(
        get_inputs=lambda: [
            SimpleNamespace(name="input_ids", type="tensor(int64)"),
            SimpleNamespace(name="attention_mask", type="tensor(int64)"),
        ]
    )
    feed = {
        "input_ids": np.array([[1, 2]], dtype=np.int32),
        "attention_mask": np.array([[1, 1]], dtype=np.int32),
    }
    normalized = _normalize_onnx_feed(session, feed)
    assert normalized["input_ids"].dtype == np.int64
    assert normalized["attention_mask"].dtype == np.int64


def test_extract_logits_falls_back_to_first_output() -> None:
    logits = np.array([[0.5, -0.5]], dtype=np.float32)
    extracted = _extract_logits([logits])
    np.testing.assert_array_equal(extracted, logits)
