"""Tokenizer loading helpers for DeBERTa training/export."""

from __future__ import annotations

from typing import Any


def load_deberta_tokenizer(model_name_or_path: str, **kwargs: Any) -> Any:
    """Load DeBERTa tokenizer; avoid fast-tokenizer regex false positives on 4.57.x."""
    from transformers import AutoTokenizer  # noqa: PLC0415

    load_kwargs: dict[str, Any] = {"use_fast": False, **kwargs}
    try:
        return AutoTokenizer.from_pretrained(model_name_or_path, fix_mistral_regex=True, **load_kwargs)
    except TypeError:
        return AutoTokenizer.from_pretrained(model_name_or_path, **load_kwargs)
