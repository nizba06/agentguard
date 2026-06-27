"""Default paths and artifact checks for the packaged risk scorer."""

from __future__ import annotations

from pathlib import Path

_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
_MODEL_FILE = "risk_scorer.onnx"
_HASH_FILE = "model.sha256"
_TOKENIZER_FILES = ("tokenizer_config.json", "tokenizer.json")


def default_model_dir() -> Path:
    """Return the directory containing bundled model artifacts."""
    return _MODEL_DIR


def default_model_path() -> Path:
    """Return the default ONNX model path."""
    return _MODEL_DIR / _MODEL_FILE


def required_model_files() -> tuple[str, ...]:
    """Filenames expected under ``agentguard/models/`` after Kaggle training."""
    return (_MODEL_FILE, _HASH_FILE, *_TOKENIZER_FILES)


def model_artifact_status(model_dir: Path | None = None) -> dict[str, bool]:
    """Report which required model files exist locally."""
    directory = model_dir or default_model_dir()
    return {name: (directory / name).exists() for name in required_model_files()}


def missing_model_files(model_dir: Path | None = None) -> list[str]:
    """Return required filenames that are not present."""
    return [name for name, present in model_artifact_status(model_dir).items() if not present]
