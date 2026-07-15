"""Fine-tune DeBERTa-v3-small for binary injection classification."""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Allow `python training/train.py` without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from training.scoring import (  # noqa: E402
    PROBE_MIN_GAP,
    injection_class_index_from_config,
    resolve_injection_class_index,
    validate_probe,
)
from training.tokenizer_utils import load_deberta_tokenizer  # noqa: E402


@dataclass
class TrainingResult:
    """Final metrics from a training run."""

    best_f1: float
    best_precision: float
    best_recall: float
    best_false_positive_rate: float
    best_epoch: int
    model_path: str
    injection_class_index: int


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                row = json.loads(line)
                row["label"] = int(row["label"])
                row["text"] = str(row["text"])
                rows.append(row)
    return rows


def _balance_train_rows(
    rows: list[dict[str, Any]],
    rng: random.Random,
    *,
    max_neg_to_pos_ratio: float = 2.0,
) -> list[dict[str, Any]]:
    """Oversample injection rows so the trainer cannot ignore the minority class."""
    pos = [row for row in rows if row["label"] == 1]
    neg = [row for row in rows if row["label"] == 0]
    if not pos or not neg:
        return rows
    target_pos = max(len(pos), int(len(neg) / max_neg_to_pos_ratio))
    balanced_pos: list[dict[str, Any]] = []
    while len(balanced_pos) < target_pos:
        balanced_pos.extend(pos)
    balanced_pos = balanced_pos[:target_pos]
    out = balanced_pos + neg
    rng.shuffle(out)
    return out


def _build_training_arguments(output_dir: Path, *, quick: bool) -> Any:
    """Build TrainingArguments compatible with installed transformers version."""
    from transformers import TrainingArguments  # noqa: PLC0415

    # Keep fp16/bf16 off: Kaggle mixed-precision saves have produced collapsed checkpoints.
    kwargs: dict[str, object] = {
        "output_dir": str(output_dir),
        "num_train_epochs": 1 if quick else 4,
        "per_device_train_batch_size": 8 if quick else 16,
        "per_device_eval_batch_size": 16 if quick else 32,
        "learning_rate": 2e-5,
        "warmup_ratio": 0.1,
        "weight_decay": 0.01,
        "max_grad_norm": 1.0,
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "fp16": False,
        "bf16": False,
        "logging_steps": 25,
        "report_to": "none",
        "save_total_limit": 2,
    }
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
    labels = np.asarray(labels)
    predictions = np.asarray(predictions)

    n_pred1 = int(np.sum(predictions == 1))
    n_label1 = int(np.sum(labels == 1))
    print(
        f"  [eval batch] labels_pos={n_label1}/{len(labels)} "
        f"pred_pos={n_pred1}/{len(predictions)}"
    )

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="binary",
        pos_label=1,
        zero_division=0,
    )
    tn = int(np.sum((predictions == 0) & (labels == 0)))
    fp = int(np.sum((predictions == 1) & (labels == 0)))
    fn = int(np.sum((predictions == 0) & (labels == 1)))
    tp = int(np.sum((predictions == 1) & (labels == 1)))
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    print(f"  [eval batch] tp={tp} fp={fp} tn={tn} fn={fn}")
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_positive_rate": float(fpr),
    }


def _score_logits(model: Any, tokenizer: Any, text: str, max_length: int) -> np.ndarray:
    import torch  # noqa: PLC0415

    model.eval()
    encoded = tokenizer(
        text,
        return_tensors="pt",
        max_length=max_length,
        truncation=True,
        padding="max_length",
    )
    device = next(model.parameters()).device
    encoded = {key: val.to(device) for key, val in encoded.items()}
    with torch.no_grad():
        logits = model(**encoded).logits.detach().float().cpu().numpy()
    return logits.reshape(-1)


def _run_probe(
    model: Any,
    tokenizer: Any,
    max_length: int,
    injection_index: int | None = None,
    *,
    injection_texts: list[str] | None = None,
    benign_texts: list[str] | None = None,
) -> tuple[float, float, int, np.ndarray, np.ndarray]:
    from training.scoring import (  # noqa: PLC0415
        BENIGN_SAMPLES,
        INJECTION_SAMPLES,
        probe_sets_with_index,
    )

    def score_logits(text: str) -> np.ndarray:
        return _score_logits(model, tokenizer, text, max_length)

    inj_texts = injection_texts or list(INJECTION_SAMPLES)
    ben_texts = benign_texts or list(BENIGN_SAMPLES)
    preferred = 1 if injection_index is None else int(injection_index)

    inj_score, ben_score, inj_logits, ben_logits = probe_sets_with_index(
        score_logits,
        preferred,
        injection_texts=inj_texts,
        benign_texts=ben_texts,
    )
    if injection_index is None:
        injection_index = resolve_injection_class_index(
            inj_logits,
            ben_logits,
            preferred_index=preferred,
        )
        inj_score, ben_score, inj_logits, ben_logits = probe_sets_with_index(
            score_logits,
            injection_index,
            injection_texts=inj_texts,
            benign_texts=ben_texts,
        )
    print(
        f"  probe mean logits inj={inj_logits.mean(axis=0)} ben={ben_logits.mean(axis=0)} "
        f"index={injection_index} argmax_inj={int(inj_logits.mean(axis=0).argmax())}"
    )
    return inj_score, ben_score, injection_index, inj_logits, ben_logits


def _held_out_probe_texts(
    rows: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> tuple[list[str], list[str]]:
    inj = [row["text"] for row in rows if row["label"] == 1][:limit]
    ben = [row["text"] for row in rows if row["label"] == 0][:limit]
    return inj, ben


def train_model(
    data_dir: str,
    output_dir: str,
    *,
    quick: bool | None = None,
    max_train_samples: int | None = None,
) -> TrainingResult:
    """Fine-tune DeBERTa-v3-small on prepared JSONL data."""
    import torch  # noqa: PLC0415
    from datasets import Dataset  # noqa: PLC0415
    from torch import nn  # noqa: PLC0415
    from transformers import (  # noqa: PLC0415
        AutoModelForSequenceClassification,
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
    rng = random.Random(42)

    train_rows = _load_jsonl(data_path / "train.jsonl")
    val_rows = _load_jsonl(data_path / "val.jsonl")
    if max_train_samples and len(train_rows) > max_train_samples:
        train_rows = train_rows[:max_train_samples]
    train_rows = _balance_train_rows(train_rows, rng)

    n_pos = sum(1 for row in train_rows if row["label"] == 1)
    n_neg = sum(1 for row in train_rows if row["label"] == 0)
    v_pos = sum(1 for row in val_rows if row["label"] == 1)
    v_neg = sum(1 for row in val_rows if row["label"] == 0)
    print("\n=== Data diagnostics ===")
    print(f"Train +/− (balanced): {n_pos}/{n_neg}")
    print(f"Val   +/−:            {v_pos}/{v_neg}")
    if n_pos == 0 or v_pos == 0:
        raise RuntimeError("No positive (injection) labels in train/val — prepare_dataset failed.")
    print("Sample positives:")
    for row in [r for r in train_rows if r["label"] == 1][:3]:
        print(f"  [1] {row['text'][:100]!r}")
    print("Sample negatives:")
    for row in [r for r in train_rows if r["label"] == 0][:3]:
        print(f"  [0] {row['text'][:100]!r}")

    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    tokenizer = load_deberta_tokenizer("microsoft/deberta-v3-small")
    model = AutoModelForSequenceClassification.from_pretrained(
        "microsoft/deberta-v3-small",
        num_labels=2,
        id2label={0: "benign", 1: "injection"},
        label2id={"benign": 0, "injection": 1},
        torch_dtype=torch.float32,
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
    cols = ["input_ids", "attention_mask", "labels"]
    for optional in ("token_type_ids",):
        if optional in train_ds.column_names:
            cols.append(optional)
    train_ds = train_ds.remove_columns(
        [name for name in train_ds.column_names if name not in cols]
    )
    val_ds = val_ds.remove_columns([name for name in val_ds.column_names if name not in cols])

    inj_weight = max(float(n_neg) / float(n_pos), 8.0)
    class_weight = torch.tensor([1.0, inj_weight], dtype=torch.float32)
    print(f"Class weight (ben/inj): {class_weight.tolist()}")

    class WeightedTrainer(Trainer):
        def compute_loss(self, model: Any, inputs: dict[str, Any], return_outputs: bool = False, **kwargs: Any) -> Any:  # noqa: ANN401
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            weight = class_weight.to(device=logits.device, dtype=logits.dtype)
            loss = nn.CrossEntropyLoss(weight=weight)(logits, labels)
            return (loss, outputs) if return_outputs else loss

    args = _build_training_arguments(out_path, quick=quick)
    trainer = WeightedTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=_compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()

    held_inj, held_ben = _held_out_probe_texts(val_rows)
    if not held_inj or not held_ben:
        raise RuntimeError("Val set missing injection or benign rows for post-train probe.")

    print("\n=== In-memory probe (before save) ===")
    print(f"Using {len(held_inj)} val injections + {len(held_ben)} val benigns")
    inj_mem, ben_mem, inj_index, _, _ = _run_probe(
        trainer.model,
        tokenizer,
        max_length,
        injection_index=1,
        injection_texts=held_inj,
        benign_texts=held_ben,
    )
    print(f"in-memory injection={inj_mem:.3f} benign={ben_mem:.3f} gap={inj_mem - ben_mem:.3f}")
    validate_probe(inj_mem, ben_mem, min_gap=PROBE_MIN_GAP, context="In-memory checkpoint")

    best_dir = out_path / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.model = trainer.model.float().cpu()
    trainer.model.config.injection_class_index = int(inj_index)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))

    print("\n=== Reloaded checkpoint probe ===")
    reloaded = AutoModelForSequenceClassification.from_pretrained(str(best_dir))
    reloaded_index = injection_class_index_from_config(reloaded.config) or inj_index
    inj, ben, resolved_index, _, _ = _run_probe(
        reloaded,
        tokenizer,
        max_length,
        injection_index=reloaded_index,
        injection_texts=held_inj,
        benign_texts=held_ben,
    )
    print(f"reloaded injection={inj:.3f} benign={ben:.3f} gap={inj - ben:.3f}")
    validate_probe(inj, ben, min_gap=PROBE_MIN_GAP, context="Reloaded checkpoint")
    reloaded.config.injection_class_index = int(resolved_index)
    reloaded.save_pretrained(str(best_dir))

    result = TrainingResult(
        best_f1=float(metrics.get("eval_f1", 0.0)),
        best_precision=float(metrics.get("eval_precision", 0.0)),
        best_recall=float(metrics.get("eval_recall", 0.0)),
        best_false_positive_rate=float(metrics.get("eval_false_positive_rate", 0.0)),
        best_epoch=int(metrics.get("epoch", 0)),
        model_path=str(best_dir),
        injection_class_index=int(resolved_index),
    )

    print("\n=== Training Complete ===")
    print(f"Quick mode:              {quick}")
    print(f"Max sequence length:     {max_length}")
    print(f"Train samples:           {len(train_rows)}")
    print(f"Injection class index:   {result.injection_class_index}")
    print(f"Best F1:                 {result.best_f1:.4f}")
    print(f"Best Precision:          {result.best_precision:.4f}")
    print(f"Best Recall:             {result.best_recall:.4f}")
    print(f"Best False Positive Rate:{result.best_false_positive_rate:.4f}")
    print(f"Model saved to:          {result.model_path}")
    print("=========================\n")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fine-tune DeBERTa for AgentGuard")
    parser.add_argument("--data-dir", default="training/data")
    parser.add_argument("--output-dir", default="training/checkpoints")
    parser.add_argument("--quick", action="store_true", help="1-epoch smoke train")
    parser.add_argument("--max-train-samples", type=int, default=None)
    cli = parser.parse_args()
    train_model(
        cli.data_dir,
        cli.output_dir,
        quick=cli.quick or None,
        max_train_samples=cli.max_train_samples,
    )
