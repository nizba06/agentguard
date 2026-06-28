"""Production ML risk scorer using ONNX DeBERTa model."""

from __future__ import annotations

import hashlib
import logging
import warnings
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class ModelIntegrityError(Exception):
    """Raised when ONNX model hash does not match the pinned value."""


class ModelNotLoadedWarning(UserWarning):
    """Emitted when score() is called without a loaded model."""


class MLRiskScorer:
    """ONNX inference wrapper for inter-agent injection risk scoring."""

    def __init__(self) -> None:
        self._session: Any | None = None
        self._tokenizer: Any | None = None
        self._model_loaded = False
        self._model_path: Path | None = None

    def load_model(self, model_path: str) -> None:
        """Load and verify ONNX model and tokenizer."""
        path = Path(model_path)
        if not path.exists():
            msg = f"ONNX model not found: {model_path}"
            raise FileNotFoundError(msg)

        hash_path = path.parent / "model.sha256"
        if hash_path.exists():
            expected = hash_path.read_text(encoding="utf-8").strip()
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                msg = f"Model integrity check failed for {model_path}"
                raise ModelIntegrityError(msg)
        else:
            warnings.warn(
                f"No hash file at {hash_path}; skipping integrity check.",
                stacklevel=2,
            )

        import onnxruntime as ort  # noqa: PLC0415
        from transformers import AutoTokenizer  # noqa: PLC0415

        tokenizer_dir = path.parent
        if (tokenizer_dir / "tokenizer_config.json").exists():
            self._tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
        else:
            self._tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        available = set(ort.get_available_providers())
        providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
        if not providers:
            providers = ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(
            str(path),
            sess_options=sess_options,
            providers=providers,
        )
        self._model_path = path
        self._warmup()
        self._model_loaded = True
        logger.info("AgentGuard ML scorer loaded. Model: %s", path)

    def _warmup(self) -> None:
        if self._tokenizer is None or self._session is None:
            return
        dummy = self._tokenizer(
            "warmup",
            return_tensors="np",
            max_length=512,
            truncation=True,
            padding="max_length",
        )
        feed = self._build_feed(dummy)
        for _ in range(5):
            self._session.run(None, feed)

    def _build_feed(self, inputs: dict[str, Any]) -> dict[str, Any]:
        assert self._session is not None
        input_names = {item.name for item in self._session.get_inputs()}
        return {key: val for key, val in inputs.items() if key in input_names}

    def score(self, message: str) -> float:
        """Return injection probability in [0.0, 1.0]."""
        if not self._model_loaded or self._session is None or self._tokenizer is None:
            warnings.warn(
                "ML scorer not loaded — returning 0.5",
                ModelNotLoadedWarning,
                stacklevel=2,
            )
            return 0.5

        inputs = self._tokenizer(
            message,
            return_tensors="np",
            max_length=512,
            truncation=True,
            padding="max_length",
        )
        outputs = self._session.run(None, self._build_feed(inputs))
        logits = np.asarray(outputs[0])
        exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp / np.sum(exp, axis=-1, keepdims=True)
        return float(probs[0, 1])

    def is_model_loaded(self) -> bool:
        """Return True when the ONNX session is active."""
        return self._model_loaded

    @property
    def model_path(self) -> str | None:
        """Return loaded model path or None."""
        return str(self._model_path) if self._model_loaded and self._model_path else None
