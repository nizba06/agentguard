"""Tests for benchmark dataset generator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from benchmarks.generate_dataset import ATTACK_CLASSES, DatasetGenerator


def _batch_result(custom_id: str, lines: list[str]) -> MagicMock:
    entry = MagicMock()
    entry.custom_id = custom_id
    entry.result.type = "succeeded"
    entry.result.message.content = [MagicMock(text="\n".join(lines))]
    return entry


@patch("benchmarks.generate_dataset.time.sleep")
def test_generate_adversarial_batch_structure(mock_sleep: MagicMock, tmp_path: Path) -> None:
    del mock_sleep
    generator = DatasetGenerator(output_dir=tmp_path)
    valid_line = json.dumps({
        "message_text": "A" * 60 + " ignore previous instructions " + "B" * 60,
        "attack_class": "INDIRECT_INJECTION",
        "target_agent": "researcher",
        "subtlety_level": 2,
        "expected_detection_layer": "rule_filter",
        "reasoning": "Contains injection pattern",
    })
    malformed = "not json at all"

    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.id = "batch_123"
    mock_client.messages.batches.create.return_value = mock_batch

    status = MagicMock()
    status.processing_status = "ended"
    mock_client.messages.batches.retrieve.return_value = status

    results = [
        _batch_result(attack_class, [valid_line, malformed])
        for attack_class in ATTACK_CLASSES
    ]
    mock_client.messages.batches.results.return_value = results
    generator._client = mock_client

    rows = generator.generate_adversarial_batch()
    assert len(rows) == len(ATTACK_CLASSES)
    assert all("message_text" in row for row in rows)
    assert all("attack_class" in row for row in rows)


@patch("benchmarks.generate_dataset.time.sleep")
def test_malformed_json_skipped(mock_sleep: MagicMock) -> None:
    del mock_sleep
    generator = DatasetGenerator()
    text = "garbage line\n" + json.dumps({"message_text": "valid example text here"})
    parsed = generator._parse_json_lines(text, default_class="PROPAGATION")
    assert len(parsed) == 1
    assert parsed[0]["attack_class"] == "PROPAGATION"


def test_save_datasets_writes_jsonl(tmp_path: Path) -> None:
    generator = DatasetGenerator(output_dir=tmp_path)
    adversarial = [{
        "message_text": "attack message",
        "attack_class": "GOAL_HIJACK",
        "subtlety_level": 3,
    }]
    benign = [{"message_text": "benign message", "label": 0, "category": "task_delegation"}]
    generator.save_datasets(adversarial, benign)

    adv_path = tmp_path / "adversarial.jsonl"
    ben_path = tmp_path / "benign.jsonl"
    readme = tmp_path / "README.md"
    assert adv_path.exists()
    assert ben_path.exists()
    assert readme.exists()

    adv_rows = [json.loads(line) for line in adv_path.read_text(encoding="utf-8").splitlines()]
    ben_rows = [json.loads(line) for line in ben_path.read_text(encoding="utf-8").splitlines()]
    assert len(adv_rows) == 1
    assert len(ben_rows) == 1
    assert adv_rows[0]["attack_class"] == "GOAL_HIJACK"
    assert ben_rows[0]["label"] == 0
