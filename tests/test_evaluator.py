"""Tests for benchmark evaluation harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentguard import AgentGuard
from benchmarks.evaluate import BenchmarkEvaluator, BenchmarkResults


@pytest.fixture
def evaluator_guard(tmp_path: Path) -> AgentGuard:
    return AgentGuard(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        enable_trust_attestation=False,
    )


def test_evaluator_runs_with_hardcoded_examples(evaluator_guard: AgentGuard) -> None:
    evaluator = BenchmarkEvaluator(evaluator_guard)
    missing = Path("benchmarks/dataset/__does_not_exist__.jsonl")
    results = evaluator.run_full_evaluation(
        adversarial_path=str(missing),
        benign_path=str(missing),
    )
    assert isinstance(results, BenchmarkResults)
    assert results.total_adversarial > 0
    assert results.total_benign > 0
    assert results.overall_detection_rate > 0
    assert results.timestamp
    assert isinstance(results.per_class, list)
    assert len(results.per_class) >= 1


def test_report_generation(evaluator_guard: AgentGuard, tmp_path: Path) -> None:
    evaluator = BenchmarkEvaluator(evaluator_guard)
    missing = tmp_path / "missing.jsonl"
    results = evaluator.run_full_evaluation(
        adversarial_path=str(missing),
        benign_path=str(missing),
    )
    report_path = tmp_path / "report.md"
    evaluator.generate_report(results, str(report_path))
    content = report_path.read_text(encoding="utf-8")
    assert "## AgentGuard Benchmark Results" in content
    assert "## Summary" in content
    assert "## Detection Rate by Attack Class" in content
    assert "## Detection by Layer" in content
    assert "## Comparison: Unprotected vs AgentGuard" in content
    assert "| Metric | Value |" in content
    assert "| Attack Class | Examples | Detected | Detection Rate | P95 Latency |" in content
