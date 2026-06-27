"""Fine-tune DeBERTa-v3-small for binary injection classification."""

from __future__ import annotations

import json
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


def _compute_metrics(eval_pred: Any) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support  # noqa: PLC0415

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0,
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


def train_model(data_dir: str, output_dir: str) -> TrainingResult:
    """Fine-tune DeBERTa-v3-small on prepared JSONL data."""
    from datasets import Dataset  # noqa: PLC0415
    from transformers import (  # noqa: PLC0415
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    data_path = Path(data_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    train_rows = _load_jsonl(data_path / "train.jsonl")
    val_rows = _load_jsonl(data_path / "val.jsonl")

    tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")
    model = AutoModelForSequenceClassification.from_pretrained(
        "microsoft/deberta-v3-small",
        num_labels=2,
    )

    def tokenize_batch(batch: dict[str, list[Any]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            max_length=512,
            truncation=True,
            padding="max_length",
        )

    train_ds = Dataset.from_list(train_rows).map(tokenize_batch, batched=True)
    val_ds = Dataset.from_list(val_rows).map(tokenize_batch, batched=True)
    train_ds = train_ds.rename_column("label", "labels")
    val_ds = val_ds.rename_column("label", "labels")

    training_kwargs: dict[str, object] = {
        "output_dir": str(out_path),
        "num_train_epochs": 4,
        "per_device_train_batch_size": 16,
        "per_device_eval_batch_size": 32,
        "learning_rate": 2e-5,
        "warmup_ratio": 0.1,
        "weight_decay": 0.01,
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1",
        "greater_is_better": True,
        "fp16": True,
        "logging_steps": 50,
        "report_to": "none",
    }
    try:
        args = TrainingArguments(eval_strategy="epoch", **training_kwargs)
    except TypeError:
        args = TrainingArguments(evaluation_strategy="epoch", **training_kwargs)

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
    print(f"Best F1:                 {result.best_f1:.4f}")
    print(f"Best Precision:          {result.best_precision:.4f}")
    print(f"Best Recall:             {result.best_recall:.4f}")
    print(f"Best False Positive Rate:{result.best_false_positive_rate:.4f}")
    print(f"Model saved to:          {result.model_path}")
    print("=========================\n")
    return result


if __name__ == "__main__":
    train_model("training/data", "training/checkpoints")
