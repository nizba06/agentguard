"""Tests for benchmark dataset generator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from benchmarks.generate_dataset import (
    ADV_CHUNK_SIZE,
    ATTACK_CLASSES,
    BATCH_CUSTOM_ID_RE,
    BENIGN_CATEGORIES,
    BENIGN_CHUNK_SIZE,
    TARGET_ADV_PER_CLASS,
    TARGET_BEN_PER_CATEGORY,
    DatasetGenerator,
    build_batch_request_specs,
    estimate_cost_usd,
    print_dry_run,
)


def test_build_batch_request_specs_counts() -> None:
    specs = build_batch_request_specs()
    adv = [s for s in specs if s.kind == "adversarial"]
    ben = [s for s in specs if s.kind == "benign"]

    assert len(adv) == len(ATTACK_CLASSES) * ((TARGET_ADV_PER_CLASS + ADV_CHUNK_SIZE - 1) // ADV_CHUNK_SIZE)
    assert len(ben) == len(BENIGN_CATEGORIES) * (
        (TARGET_BEN_PER_CATEGORY + BENIGN_CHUNK_SIZE - 1) // BENIGN_CHUNK_SIZE
    )
    assert all(s.chunk_size <= (ADV_CHUNK_SIZE if s.kind == "adversarial" else BENIGN_CHUNK_SIZE) for s in specs)
    assert len({s.custom_id for s in specs}) == len(specs)
    assert all(BATCH_CUSTOM_ID_RE.fullmatch(s.custom_id) for s in specs)


def test_estimate_cost_returns_range() -> None:
    specs = build_batch_request_specs()
    low, high = estimate_cost_usd(specs)
    assert low > 0
    assert high >= low


def test_dry_run_prints(capsys) -> None:
    print_dry_run(build_batch_request_specs())
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "6200" in out.replace(",", "")
    assert "claude-haiku-4-5-20251001" in out
    assert "claude-sonnet-4-5-20250929" in out


def test_format_batch_error_includes_api_message() -> None:
    entry = MagicMock()
    entry.result.type = "errored"
    entry.result.error.type = "invalid_request_error"
    entry.result.error.message = "model not found"
    assert "invalid_request_error" in DatasetGenerator._format_batch_error(entry)
    assert "model not found" in DatasetGenerator._format_batch_error(entry)


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("benchmarks.generate_dataset.time.sleep")
def test_run_one_batch_validates_and_saves(mock_sleep: MagicMock, tmp_path: Path) -> None:
    del mock_sleep
    generator = DatasetGenerator(output_dir=tmp_path)
    specs = build_batch_request_specs()

    def make_adv_line(attack_class: str, idx: int) -> str:
        return json.dumps(
            {
                "message_text": " ".join([f"word{idx}"] * 50) + f" {attack_class} injection attempt {idx}.",
                "attack_class": attack_class,
                "target_agent": "researcher",
                "subtlety_level": 3,
                "expected_detection_layer": "both",
                "reasoning": "test",
            },
        )

    def make_ben_line(category: str, idx: int) -> str:
        return json.dumps(
            {
                "message_text": " ".join([f"coord{idx}"] * 20) + f" {category} routine update {idx}.",
                "label": 0,
                "category": category,
            },
        )

    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.id = "batch_test_001"
    mock_client.messages.batches.create.return_value = mock_batch

    status = MagicMock()
    status.processing_status = "ended"
    status.request_counts.processing = 0
    status.request_counts.succeeded = len(specs)
    status.request_counts.errored = 0
    status.request_counts.canceled = 0
    status.request_counts.expired = 0
    mock_client.messages.batches.retrieve.return_value = status

    results = []
    for spec in specs:
        entry = MagicMock()
        entry.custom_id = spec.custom_id
        entry.result.type = "succeeded"
        if spec.kind == "adversarial":
            lines = [
                make_adv_line(spec.attack_class or "", spec.chunk_index * 100 + i)
                for i in range(spec.chunk_size)
            ]
        else:
            lines = [
                make_ben_line(spec.category or "", spec.chunk_index * 100 + i)
                for i in range(spec.chunk_size)
            ]
        entry.result.message.content = [MagicMock(text="\n".join(lines))]
        results.append(entry)

    mock_client.messages.batches.results.return_value = results
    generator._client = mock_client

    adversarial, benign = generator.run_one_batch(specs)
    assert len(adversarial) == TARGET_ADV_PER_CLASS * len(ATTACK_CLASSES)
    assert len(benign) == TARGET_BEN_PER_CATEGORY * len(BENIGN_CATEGORIES)
    assert (tmp_path / "adversarial.jsonl").exists()
    assert (tmp_path / "benign.jsonl").exists()
    assert (tmp_path / "generation_manifest.json").exists()


def test_malformed_json_skipped() -> None:
    generator = DatasetGenerator()
    text = "garbage line\n" + json.dumps({"message_text": "valid example text here with enough words " * 3})
    parsed = generator._parse_json_lines(text, default_class="PROPAGATION")
    assert len(parsed) == 1
    assert parsed[0]["attack_class"] == "PROPAGATION"


def test_validate_counts_detects_deficit() -> None:
    errors = DatasetGenerator.validate_counts([], [])
    assert errors
    assert any("adversarial/INDIRECT_INJECTION" in err for err in errors)


def test_trim_to_targets_drops_surplus_benign() -> None:
    benign = [
        {"message_text": "x " * 10, "label": 0, "category": "clarification_request"}
        for _ in range(1001)
    ]
    adv, ben = DatasetGenerator._trim_to_targets([], benign)
    assert adv == []
    assert len(ben) == TARGET_BEN_PER_CATEGORY
