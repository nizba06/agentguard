"""Contextual consistency check via sentence-transformer embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

DEFAULT_THRESHOLD = 0.10
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class ConsistencyResult:
    """Semantic consistency check outcome."""

    consistent: bool
    similarity_score: float


class ConsistencyChecker:
    """Compare message intent against a declared pipeline task objective."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold
        self._objective: str | None = None
        self._model: Any = None
        self._objective_embedding: np.ndarray | None = None

    def set_task_objective(self, objective: str) -> None:
        """Set or update the pipeline task objective.

        Args:
            objective: Declared task objective for consistency comparison.
        """
        self._objective = objective
        self._objective_embedding = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        except ImportError:
            self._model = False
            return
        self._model = SentenceTransformer(DEFAULT_MODEL)

    def _embed(self, text: str) -> np.ndarray:
        self._ensure_model()
        if self._model is False or self._model is None:
            return np.zeros(384, dtype=np.float64)
        vector = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(vector, dtype=np.float64)

    def check(self, message: str) -> ConsistencyResult:
        """Check message semantic similarity to the task objective.

        Args:
            message: Message text to evaluate.

        Returns:
            ConsistencyResult with similarity score and pass/fail flag.
        """
        if not self._objective:
            return ConsistencyResult(consistent=True, similarity_score=1.0)
        if self._model is False:
            return ConsistencyResult(consistent=True, similarity_score=1.0)
        if self._objective_embedding is None:
            self._objective_embedding = self._embed(self._objective)
        assert self._objective_embedding is not None
        message_embedding = self._embed(message)
        similarity = float(np.dot(self._objective_embedding, message_embedding))
        return ConsistencyResult(
            consistent=similarity >= self._threshold,
            similarity_score=similarity,
        )
