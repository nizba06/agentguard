"""Tests for AppendOnlyLogger."""

from __future__ import annotations

import json
from pathlib import Path

from agentguard.audit.logger import AppendOnlyLogger, _sha256_hex


def test_sha256_hex_deterministic() -> None:
    assert _sha256_hex(b"hello") == _sha256_hex(b"hello")


def test_write_entry_chains(tmp_path: Path) -> None:
    logger = AppendOnlyLogger(tmp_path / "audit.jsonl")
    logger.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.1,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview="hello",
        payload_bytes=b"hello",
    )
    logger.write_entry(
        sender_id="b",
        recipient_id="c",
        risk_score=0.9,
        trust_result="PASS",
        capability_result="SKIP",
        action="QUARANTINE",
        failure_reason="rule_filter",
        message_preview="bad",
        payload_bytes=b"bad",
    )
    ok, err = logger.verify_chain()
    assert ok, err
    assert len(logger.entries) == 2
    assert logger.entries[1].prev_hash != "0" * 64


def test_verify_chain_detects_tampering(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    logger = AppendOnlyLogger(log_path)
    logger.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview=None,
        payload_bytes=b"x",
    )
    logger.write_entry(
        sender_id="b",
        recipient_id="c",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview=None,
        payload_bytes=b"y",
    )
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[1])
    record["prev_hash"] = "f" * 64
    lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, err = AppendOnlyLogger(log_path).verify_chain()
    assert not ok
    assert err is not None


def test_resume_chain_from_existing_log(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    first = AppendOnlyLogger(log_path)
    first.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview=None,
        payload_bytes=b"x",
    )
    second = AppendOnlyLogger(log_path)
    second.write_entry(
        sender_id="b",
        recipient_id="c",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview=None,
        payload_bytes=b"y",
    )
    ok, err = second.verify_chain()
    assert ok, err


def test_verify_chain_from_file(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    logger = AppendOnlyLogger(log_path)
    logger.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview=None,
        payload_bytes=b"x",
    )
    ok, err = AppendOnlyLogger().verify_chain(log_path)
    assert ok, err


def test_payload_not_stored_in_entry() -> None:
    logger = AppendOnlyLogger()
    entry = logger.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.0,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason=None,
        message_preview="secret preview",
        payload_bytes=b"secret payload bytes",
    )
    assert entry.message_hash == _sha256_hex(b"secret payload bytes")
    assert "secret payload bytes" not in json.dumps(entry.__dict__)
