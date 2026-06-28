"""Fine-tune DeBERTa-v3-small for binary injection classification."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class TrainingResult:
    """Final metrics from a training run."""

    best_f1: float
    best_precision: float
    best_recall: float
    best_false_positive_rate: float
    best_epoch: int
    model_path: str


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _build_training_arguments(output_dir: Path, *, quick: bool) -> Any:
    """Build TrainingArguments compatible with installed transformers version."""
    from transformers import TrainingArguments  # noqa: PLC0415

    kwargs: dict[str, object] = {
        "output_dir": str(output_dir),
        "num_train_epochs": 1 if quick else 4,
        "per_device_train_batch_size": 8 if quick else 16,
        "per_device_eval_batch_size": 16 if quick else 32,
        "learning_rate": 2e-5,
        "warmup_ratio": 0.1,
        "weight_decay": 0.01,
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1",
        "greater_is_better": True,
        "fp16": False,
        "logging_steps": 25,
        "report_to": "none",
        "save_total_limit": 2,
    }
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available() and not quick:
            kwargs["fp16"] = True
    except ImportError:
        pass
    eval_kwargs = ("eval_strategy", "evaluation_strategy")
    last_error: TypeError | None = None
    for key in eval_kwargs:
        try:
            return TrainingArguments(**kwargs, **{key: "epoch"})
        except TypeError as exc:
            last_error = exc
    msg = f"Unable to construct TrainingArguments: {last_error}"
    raise TypeError(msg) from last_error


def _compute_metrics(eval_pred: Any) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support  # noqa: PLC0415

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="binary",
        zero_division=0,
    )
    tn = int(np.sum((predictions == 0) & (labels == 0)))
    fp = int(np.sum((predictions == 1) & (labels == 0)))
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_positive_rate": float(fpr),
    }


def train_model(
    data_dir: str,
    output_dir: str,
    *,
    quick: bool | None = None,
    max_train_samples: int | None = None,
) -> TrainingResult:
    """Fine-tune DeBERTa-v3-small on prepared JSONL data."""
    from datasets import Dataset  # noqa: PLC0415
    from transformers import (  # noqa: PLC0415
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
    )

    if quick is None:
        quick = os.environ.get("AGENTGUARD_TRAIN_QUICK", "").lower() in {"1", "true", "yes"}
    if max_train_samples is None and quick:
        max_train_samples = int(os.environ.get("AGENTGUARD_TRAIN_MAX_SAMPLES", "2000"))
    max_length = 128 if quick else 512

    data_path = Path(data_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    train_rows = _load_jsonl(data_path / "train.jsonl")
    val_rows = _load_jsonl(data_path / "val.jsonl")
    if max_train_samples and len(train_rows) > max_train_samples:
        train_rows = train_rows[:max_train_samples]

    tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")
    model = AutoModelForSequenceClassification.from_pretrained(
        "microsoft/deberta-v3-small",
        num_labels=2,
    )

    def tokenize_batch(batch: dict[str, list[Any]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            max_length=max_length,
            truncation=True,
            padding="max_length",
        )

    train_ds = Dataset.from_list(train_rows).map(tokenize_batch, batched=True)
    val_ds = Dataset.from_list(val_rows).map(tokenize_batch, batched=True)
    train_ds = train_ds.rename_column("label", "labels")
    val_ds = val_ds.rename_column("label", "labels")

    args = _build_training_arguments(out_path, quick=quick)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=_compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()

    best_dir = out_path / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))

    result = TrainingResult(
        best_f1=float(metrics.get("eval_f1", 0.0)),
        best_precision=float(metrics.get("eval_precision", 0.0)),
        best_recall=float(metrics.get("eval_recall", 0.0)),
        best_false_positive_rate=float(metrics.get("eval_false_positive_rate", 0.0)),
        best_epoch=int(metrics.get("epoch", 0)),
        model_path=str(best_dir),
    )

    print("\n=== Training Complete ===")
    print(f"Quick mode:              {quick}")
    print(f"Max sequence length:     {max_length}")
    print(f"Train samples:           {len(train_rows)}")
    print(f"Best F1:                 {result.best_f1:.4f}")
    print(f"Best Precision:          {result.best_precision:.4f}")
    print(f"Best Recall:             {result.best_recall:.4f}")
    print(f"Best False Positive Rate:{result.best_false_positive_rate:.4f}")
    print(f"Model saved to:          {result.model_path}")
    print("=========================\n")
    return result


if __name__ == "__main__":
    train_model("training/data", "training/checkpoints")
