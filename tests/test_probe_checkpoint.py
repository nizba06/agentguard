"""Smoke tests for shared scoring helpers and probe_checkpoint imports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from training import probe_checkpoint
from training.scoring import (
    PROBE_MIN_GAP,
    extract_classification_logits,
    load_probe_texts_from_jsonl,
    mean_injection_probability,
    normalize_onnx_int_feed,
    resolve_probe_texts,
)


def test_probe_checkpoint_exports_scoring_helpers() -> None:
    assert callable(probe_checkpoint.mean_injection_probability)
    assert callable(probe_checkpoint.extract_classification_logits)
    assert PROBE_MIN_GAP == 0.3
    assert callable(probe_checkpoint.resolve_probe_texts)


def test_extract_classification_logits_prefers_two_class_output() -> None:
    logits = np.array([[1.0, 3.0]], dtype=np.float32)
    hidden = np.zeros((1, 768), dtype=np.float32)
    extracted = extract_classification_logits([hidden, logits])
    np.testing.assert_array_equal(extracted, logits)


def test_normalize_onnx_int_feed_casts_inputs() -> None:
    from types import SimpleNamespace

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
    normalized = normalize_onnx_int_feed(session, feed)
    assert normalized["input_ids"].dtype == np.int64
    assert mean_injection_probability(np.array([[0.0, 5.0]]), 1) > 0.9


def test_load_probe_texts_from_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "val.jsonl"
    rows = [
        {"text": "injection example one", "label": 1},
        {"text": "benign example one", "label": 0},
        {"text": "injection example two", "label": 1},
        {"text": "benign example two", "label": 0},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    loaded = load_probe_texts_from_jsonl(path, limit=2)
    assert loaded is not None
    inj, ben = loaded
    assert inj == ["injection example one", "injection example two"]
    assert ben == ["benign example one", "benign example two"]


def test_resolve_probe_texts_prefers_val_jsonl(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "val.jsonl").write_text(
        json.dumps({"text": "val inj", "label": 1})
        + "\n"
        + json.dumps({"text": "val ben", "label": 0})
        + "\n",
        encoding="utf-8",
    )
    inj, ben, source = resolve_probe_texts(data_dir=data_dir, limit=1)
    assert inj == ["val inj"]
    assert ben == ["val ben"]
    assert "val.jsonl" in source
