"""Tests for bundled model path helpers."""

from __future__ import annotations

from pathlib import Path

from agentguard.inspector.model_paths import (
    default_model_dir,
    default_model_path,
    missing_model_files,
    model_artifact_status,
    required_model_files,
)


def test_default_model_dir_under_package() -> None:
    model_dir = default_model_dir()
    assert model_dir.name == "models"
    assert model_dir.parent.name == "agentguard"


def test_default_model_path_points_to_onnx() -> None:
    assert default_model_path().name == "risk_scorer.onnx"
    assert default_model_path().parent == default_model_dir()


def test_required_model_files_includes_onnx_and_tokenizer() -> None:
    names = required_model_files()
    assert "risk_scorer.onnx" in names
    assert "model.sha256" in names
    assert "tokenizer.json" in names


def test_model_artifact_status_for_empty_dir(tmp_path: Path) -> None:
    status = model_artifact_status(tmp_path)
    assert all(name in status for name in required_model_files())
    assert not any(status.values())


def test_missing_model_files_lists_absent_artifacts(tmp_path: Path) -> None:
    (tmp_path / "risk_scorer.onnx").write_bytes(b"onnx")
    missing = missing_model_files(tmp_path)
    assert "risk_scorer.onnx" not in missing
    assert "model.sha256" in missing
