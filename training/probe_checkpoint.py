"""Score HF checkpoint and/or ONNX with injection vs benign probes.

Used on Kaggle after train/export to catch collapsed or swapped models
before you download artifacts. Prefers prepared val.jsonl texts (same
distribution as training) over built-in fixed strings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Allow `python training/probe_checkpoint.py` without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from training.scoring import (  # noqa: E402
    PROBE_MIN_GAP,
    extract_classification_logits,
    mean_injection_probability,
    normalize_onnx_int_feed,
    resolve_injection_class_index,
    resolve_probe_texts,
    validate_probe,
)
from training.tokenizer_utils import load_deberta_tokenizer  # noqa: E402


def _load_injection_index(model_dir: Path) -> int:
    scorer_config = model_dir / "scorer_config.json"
    if scorer_config.exists():
        return int(json.loads(scorer_config.read_text(encoding="utf-8"))["injection_class_index"])
    config_path = model_dir / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("injection_class_index") is not None:
            return int(config["injection_class_index"])
        for idx, name in (config.get("id2label") or {}).items():
            if str(name).lower() == "injection":
                return int(idx)
    return 1


def score_hf_batch(checkpoint: Path, texts: tuple[str, ...] | list[str]) -> np.ndarray:
    import torch
    from transformers import AutoModelForSequenceClassification

    tokenizer = load_deberta_tokenizer(str(checkpoint))
    model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint)).eval().float().cpu()
    logits_rows: list[np.ndarray] = []
    with torch.no_grad():
        for text in texts:
            encoded = tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding="max_length",
            )
            logits_rows.append(model(**encoded).logits.numpy().reshape(-1))
    return np.stack(logits_rows, axis=0)


def score_onnx_batch(model_dir: Path, texts: tuple[str, ...] | list[str]) -> np.ndarray:
    import onnxruntime as ort

    onnx_path = model_dir / "risk_scorer.onnx"
    tokenizer = load_deberta_tokenizer(str(model_dir))
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    names = {item.name for item in session.get_inputs()}
    logits_rows: list[np.ndarray] = []
    for text in texts:
        encoded = tokenizer(
            text,
            return_tensors="np",
            max_length=512,
            truncation=True,
            padding="max_length",
        )
        feed = normalize_onnx_int_feed(
            session, {key: val for key, val in encoded.items() if key in names}
        )
        logits_rows.append(extract_classification_logits(session.run(None, feed)).reshape(-1))
    return np.stack(logits_rows, axis=0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe injection vs benign scores")
    parser.add_argument("--checkpoint", default="training/checkpoints/best")
    parser.add_argument("--onnx-dir", default="agentguard/models")
    parser.add_argument("--data-dir", default="training/data")
    parser.add_argument("--hf-only", action="store_true")
    parser.add_argument("--onnx-only", action="store_true")
    parser.add_argument("--min-gap", type=float, default=PROBE_MIN_GAP)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    inj_texts, ben_texts, source = resolve_probe_texts(data_dir=args.data_dir, limit=args.limit)
    print(f"Probe texts from {source} ({len(inj_texts)} inj / {len(ben_texts)} ben)")

    results: list[tuple[str, float, float, int]] = []

    if not args.onnx_only:
        ckpt = Path(args.checkpoint)
        if not ckpt.exists():
            print(f"HF checkpoint missing: {ckpt}", file=sys.stderr)
            return 1
        inj_logits = score_hf_batch(ckpt, inj_texts)
        ben_logits = score_hf_batch(ckpt, ben_texts)
        injection_index = _load_injection_index(ckpt)
        injection_index = resolve_injection_class_index(
            inj_logits,
            ben_logits,
            preferred_index=injection_index,
        )
        inj = mean_injection_probability(inj_logits, injection_index)
        ben = mean_injection_probability(ben_logits, injection_index)
        results.append(("HF", inj, ben, injection_index))
        print(
            f"HF  index={injection_index} injection={inj:.3f}  benign={ben:.3f}  gap={inj - ben:.3f}"
        )

    if not args.hf_only:
        models = Path(args.onnx_dir)
        if not (models / "risk_scorer.onnx").exists():
            print(f"ONNX missing under {models}", file=sys.stderr)
            return 1
        injection_index = _load_injection_index(models)
        inj_logits = score_onnx_batch(models, inj_texts)
        ben_logits = score_onnx_batch(models, ben_texts)
        injection_index = resolve_injection_class_index(
            inj_logits,
            ben_logits,
            preferred_index=injection_index,
        )
        inj = mean_injection_probability(inj_logits, injection_index)
        ben = mean_injection_probability(ben_logits, injection_index)
        results.append(("ONNX", inj, ben, injection_index))
        print(
            f"ONNX index={injection_index} injection={inj:.3f}  benign={ben:.3f}  gap={inj - ben:.3f}"
        )

    failed = False
    for label, inj, ben, _idx in results:
        try:
            validate_probe(inj, ben, min_gap=args.min_gap, context=label)
        except RuntimeError as exc:
            print(f"FAIL {exc}", file=sys.stderr)
            failed = True

    if failed:
        return 2
    print("PASS: probe scores look discriminative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
