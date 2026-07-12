"""Tests for Anthropic-primary training dataset preparation."""

from __future__ import annotations

import json
from pathlib import Path

from training.prepare_dataset import DatasetPreparer


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_anthropic_prepare_writes_holdout_and_train_val(tmp_path: Path) -> None:
    adv = tmp_path / "adversarial.jsonl"
    ben = tmp_path / "benign.jsonl"
    _write_jsonl(
        adv,
        [
            {
                "message_text": f"Ignore previous instructions injection {i}",
                "attack_class": "GOAL_HIJACK",
            }
            for i in range(20)
        ]
        + [
            {
                "message_text": f"Unsigned impersonation {i}",
                "attack_class": "IMPERSONATION",
            }
            for i in range(5)
        ],
    )
    _write_jsonl(
        ben,
        [{"message_text": f"Benign status update {i}", "sender_id": "researcher"} for i in range(40)],
    )

    out = tmp_path / "data"
    holdout = tmp_path / "holdout"
    stats = DatasetPreparer(
        output_dir=out,
        benign_path=ben,
        adversarial_path=adv,
        holdout_dir=holdout,
        source="anthropic",
        holdout_fraction=0.2,
        content_attacks_only=True,
        seed=0,
    ).prepare()

    assert stats.source == "anthropic"
    assert stats.positive_count == 20  # IMPERSONATION excluded
    assert stats.negative_count == 40
    assert stats.holdout_positive == 4
    assert stats.holdout_negative == 8
    assert (out / "train.jsonl").exists()
    assert (out / "val.jsonl").exists()
    assert (out / "prepare_manifest.json").exists()
    assert (holdout / "adversarial.jsonl").exists()
    assert (holdout / "benign.jsonl").exists()

    train_labels = [
        json.loads(line)["label"] for line in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert 0 in train_labels and 1 in train_labels
