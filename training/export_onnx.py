"""Export fine-tuned checkpoint to ONNX and verify inference."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

# Allow `python training/export_onnx.py` without an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from training.scoring import (  # noqa: E402
    PROBE_MIN_GAP,
    extract_classification_logits,
    injection_class_index_from_config,
    injection_probability,
    normalize_onnx_int_feed,
    probe_sets_with_index,
    resolve_injection_class_index,
    resolve_probe_texts,
    validate_probe,
)
from training.tokenizer_utils import load_deberta_tokenizer  # noqa: E402


@dataclass
class ExportResult:
    """ONNX export metadata."""

    model_path: str
    model_size_mb: float
    sha256_hash: str
    sample_latency_ms: float
    injection_class_index: int


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_checkpoint_weights(checkpoint: Path) -> None:
    has_weights = any(checkpoint.glob("*.safetensors")) or any(checkpoint.glob("pytorch_model.bin"))
    if not has_weights:
        msg = (
            f"No model weights found in {checkpoint}. "
            "Run training/train.py successfully before export."
        )
        raise FileNotFoundError(msg)


def _normalize_onnx_feed(session: Any, feed: dict[str, Any]) -> dict[str, Any]:
    """Cast integer ONNX inputs to int64 (DeBERTa ONNX graphs require this)."""
    return normalize_onnx_int_feed(session, feed)


def _extract_logits(outputs: list[Any]) -> np.ndarray:
    """Return the [batch, num_labels] logits tensor from an ONNX session run."""
    return extract_classification_logits(outputs)


def _write_injection_index(checkpoint: Path, injection_index: int) -> None:
    """Persist injection_class_index without rewriting model weights."""
    config_path = checkpoint / "config.json"
    if not config_path.exists():
        return
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["injection_class_index"] = int(injection_index)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _resolve_injection_index(
    checkpoint: Path,
    score_logits: Callable[[str], np.ndarray],
    *,
    injection_texts: list[str],
    benign_texts: list[str],
) -> int:
    configured = None
    config_path = checkpoint / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        configured = config.get("injection_class_index")
        if configured is not None:
            return int(configured)
        for idx, name in (config.get("id2label") or {}).items():
            if str(name).lower() == "injection":
                return int(idx)

    _, _, inj_logits, ben_logits = probe_sets_with_index(
        score_logits,
        1,
        injection_texts=injection_texts,
        benign_texts=benign_texts,
    )
    return resolve_injection_class_index(inj_logits, ben_logits, preferred_index=1)


def _probe_hf_checkpoint(
    checkpoint: Path,
    *,
    injection_texts: list[str],
    benign_texts: list[str],
) -> tuple[float, float, int]:
    import torch  # noqa: PLC0415
    from transformers import AutoModelForSequenceClassification  # noqa: PLC0415

    tokenizer = load_deberta_tokenizer(str(checkpoint))
    model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint))
    model.eval()
    model = model.float().cpu()

    def score_logits(text: str) -> np.ndarray:
        encoded = tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding="max_length",
        )
        with torch.no_grad():
            logits = model(**encoded).logits.detach().cpu().numpy()
        return logits.reshape(-1)

    injection_index = _resolve_injection_index(
        checkpoint,
        score_logits,
        injection_texts=injection_texts,
        benign_texts=benign_texts,
    )
    if injection_class_index_from_config(model.config) != injection_index:
        model.config.injection_class_index = int(injection_index)
        _write_injection_index(checkpoint, injection_index)

    inj, ben, inj_logits, ben_logits = probe_sets_with_index(
        score_logits,
        injection_index,
        injection_texts=injection_texts,
        benign_texts=benign_texts,
    )
    print("\n=== HF checkpoint probe ===")
    print(
        f"  injection_index={injection_index} "
        f"inj_logits_mean={inj_logits.mean(axis=0)} ben_logits_mean={ben_logits.mean(axis=0)}"
    )
    print(f"  injection={inj:.3f}  benign={ben:.3f}  gap={inj - ben:.3f}")
    return inj, ben, injection_index


def _validate_onnx_probe(
    session: Any,
    tokenizer: Any,
    injection_index: int,
    *,
    injection_texts: list[str],
    benign_texts: list[str],
    min_gap: float = PROBE_MIN_GAP,
) -> tuple[float, float]:
    def score_onnx(text: str) -> np.ndarray:
        inputs = tokenizer(
            text,
            return_tensors="np",
            max_length=512,
            truncation=True,
            padding="max_length",
        )
        input_names = {item.name for item in session.get_inputs()}
        feed = _normalize_onnx_feed(session, {k: v for k, v in inputs.items() if k in input_names})
        return _extract_logits(session.run(None, feed)).reshape(-1)

    print("\n=== Sample Scores ===")
    inj_scores: list[float] = []
    ben_scores: list[float] = []
    for label, samples in (("INJECTION", injection_texts), ("BENIGN", benign_texts)):
        print(f"\n{label}:")
        for text in samples:
            logits = score_onnx(text)
            prob = injection_probability(logits, injection_index)
            print(f"  [{prob:.3f}] logits={logits} {text[:70]}...")
            if label == "INJECTION":
                inj_scores.append(prob)
            else:
                ben_scores.append(prob)

    mean_inj = sum(inj_scores) / len(inj_scores)
    mean_ben = sum(ben_scores) / len(ben_scores)
    validate_probe(mean_inj, mean_ben, min_gap=min_gap, context="Exported ONNX")
    return mean_inj, mean_ben


def _pick_onnx_file(root: Path) -> Path | None:
    candidates = sorted(root.rglob("*.onnx"))
    if not candidates:
        return None
    for name in ("model.onnx", "model_optimized.onnx"):
        matches = [path for path in candidates if path.name == name]
        if matches:
            return matches[0]
    return candidates[0]


def _export_with_optimum_cli(checkpoint: Path, staging_dir: Path) -> Path | None:
    staging_dir.mkdir(parents=True, exist_ok=True)
    commands = (
        [
            sys.executable,
            "-m",
            "optimum.cli",
            "export",
            "onnx",
            "--model",
            str(checkpoint),
            "--task",
            "text-classification",
            "--device",
            "cpu",
            "--dtype",
            "fp32",
            str(staging_dir),
        ],
        [
            "optimum-cli",
            "export",
            "onnx",
            "--model",
            str(checkpoint),
            "--task",
            "text-classification",
            "--device",
            "cpu",
            "--dtype",
            "fp32",
            str(staging_dir),
        ],
    )
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            continue
        if result.returncode != 0:
            print(f"optimum-cli failed ({cmd[0]}): {result.stderr[-500:]}")
            continue
        picked = _pick_onnx_file(staging_dir)
        if picked is not None:
            return picked
    return None


def _export_with_optimum_api(checkpoint: Path, dest_onnx: Path) -> bool:
    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification  # noqa: PLC0415
    except ImportError:
        return False

    staging_dir = dest_onnx.parent / "_optimum_api_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    try:
        model = ORTModelForSequenceClassification.from_pretrained(
            str(checkpoint),
            export=True,
        )
        model.save_pretrained(str(staging_dir))
        picked = _pick_onnx_file(staging_dir)
        if picked is None:
            return False
        dest_onnx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(picked, dest_onnx)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"optimum API export failed: {exc}")
        return False
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _export_with_torch(checkpoint: Path, dest_onnx: Path) -> None:
    import torch  # noqa: PLC0415
    from torch import nn  # noqa: PLC0415
    from transformers import AutoModelForSequenceClassification  # noqa: PLC0415

    model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint))
    tokenizer = load_deberta_tokenizer(str(checkpoint))
    model.eval()
    model = model.float().cpu()

    encoded = tokenizer(
        "warmup",
        return_tensors="pt",
        max_length=512,
        truncation=True,
        padding="max_length",
    )
    input_ids = encoded["input_ids"]
    attention_mask = encoded["attention_mask"]

    class _OnnxWrapper(nn.Module):
        def __init__(self, inner: nn.Module) -> None:
            super().__init__()
            self.inner = inner

        def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
            return self.inner(input_ids=input_ids, attention_mask=attention_mask).logits

    wrapped = _OnnxWrapper(model)
    dest_onnx.parent.mkdir(parents=True, exist_ok=True)
    export_kwargs: dict[str, Any] = {
        "input_names": ["input_ids", "attention_mask"],
        "output_names": ["logits"],
        "dynamic_axes": {
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        "opset_version": 14,
    }
    try:
        torch.onnx.export(
            wrapped,
            (input_ids, attention_mask),
            str(dest_onnx),
            dynamo=False,
            **export_kwargs,
        )
    except TypeError:
        torch.onnx.export(
            wrapped,
            (input_ids, attention_mask),
            str(dest_onnx),
            **export_kwargs,
        )


def _copy_optimum_cli_export(checkpoint: Path, staging_root: Path, dest_onnx: Path) -> None:
    cli_dir = staging_root / "optimum_cli"
    if cli_dir.exists():
        shutil.rmtree(cli_dir)
    picked = _export_with_optimum_cli(checkpoint, cli_dir)
    if picked is None:
        msg = "optimum-cli produced no ONNX file"
        raise FileNotFoundError(msg)
    shutil.copy2(picked, dest_onnx)


def _try_export(
    name: str,
    export_fn: Callable[[], None],
    dest_onnx: Path,
    tokenizer: Any,
    injection_index: int,
    *,
    injection_texts: list[str],
    benign_texts: list[str],
) -> bool:
    import onnxruntime as ort  # noqa: PLC0415

    if dest_onnx.exists():
        dest_onnx.unlink()
    try:
        export_fn()
    except Exception as exc:  # noqa: BLE001
        print(f"{name} export raised: {exc}")
        return False
    if not dest_onnx.exists():
        print(f"{name} export did not produce {dest_onnx}")
        return False

    session = ort.InferenceSession(str(dest_onnx), providers=["CPUExecutionProvider"])
    try:
        _validate_onnx_probe(
            session,
            tokenizer,
            injection_index,
            injection_texts=injection_texts,
            benign_texts=benign_texts,
        )
    except RuntimeError as exc:
        print(f"{name} export failed validation: {exc}")
        dest_onnx.unlink(missing_ok=True)
        return False
    print(f"{name} export passed ONNX probe.")
    return True


def export_to_onnx(
    checkpoint_dir: str,
    output_path: str,
    *,
    quantize: bool = False,
    data_dir: str = "training/data",
) -> ExportResult:
    """Export checkpoint to ONNX, copy to agentguard/models, benchmark latency."""
    checkpoint = Path(checkpoint_dir)
    if not checkpoint.exists():
        msg = f"Checkpoint directory not found: {checkpoint_dir}"
        raise FileNotFoundError(msg)
    _require_checkpoint_weights(checkpoint)

    injection_texts, benign_texts, probe_source = resolve_probe_texts(data_dir=data_dir)
    print(f"Export probes from {probe_source}")

    hf_inj, hf_ben, injection_index = _probe_hf_checkpoint(
        checkpoint,
        injection_texts=injection_texts,
        benign_texts=benign_texts,
    )
    validate_probe(hf_inj, hf_ben, min_gap=PROBE_MIN_GAP, context="HF checkpoint")

    models_dir = Path("agentguard/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    dest_onnx = models_dir / "risk_scorer.onnx"
    staging_dir = Path(output_path) / "_onnx_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    tokenizer = load_deberta_tokenizer(str(checkpoint))
    tokenizer.model_input_names = ["input_ids", "attention_mask"]

    trial_onnx = staging_dir / "trial.onnx"
    staging_dir.mkdir(parents=True, exist_ok=True)

    def export_torch() -> None:
        _export_with_torch(checkpoint, trial_onnx)

    def export_optimum_cli() -> None:
        _copy_optimum_cli_export(checkpoint, staging_dir, trial_onnx)

    def export_optimum_api() -> None:
        if not _export_with_optimum_api(checkpoint, trial_onnx):
            msg = "optimum API export failed"
            raise RuntimeError(msg)

    exporters: list[tuple[str, Callable[[], None]]] = [
        ("torch", export_torch),
        ("optimum-cli", export_optimum_cli),
        ("optimum-api", export_optimum_api),
    ]

    exported = False
    for name, export_fn in exporters:
        print(f"\nTrying {name} ONNX export...")
        if _try_export(
            name,
            export_fn,
            trial_onnx,
            tokenizer,
            injection_index,
            injection_texts=injection_texts,
            benign_texts=benign_texts,
        ):
            shutil.copy2(trial_onnx, dest_onnx)
            exported = True
            break

    shutil.rmtree(staging_dir, ignore_errors=True)

    if not exported:
        msg = (
            "All ONNX export strategies failed validation. "
            f"HF checkpoint probe passed (inj={hf_inj:.3f}, ben={hf_ben:.3f}) "
            "so the failure is in the export path, not training."
        )
        raise RuntimeError(msg)

    if quantize:
        dest_onnx = _quantize_onnx_dynamic(dest_onnx)
        import onnxruntime as ort  # noqa: PLC0415

        session = ort.InferenceSession(str(dest_onnx), providers=["CPUExecutionProvider"])
        _validate_onnx_probe(
            session,
            tokenizer,
            injection_index,
            injection_texts=injection_texts,
            benign_texts=benign_texts,
        )

    sha256 = _sha256_file(dest_onnx)
    (models_dir / "model.sha256").write_text(sha256 + "\n", encoding="utf-8")
    tokenizer.save_pretrained(str(models_dir))
    _write_scorer_metadata(models_dir, injection_index)

    import onnxruntime as ort  # noqa: PLC0415

    session = ort.InferenceSession(str(dest_onnx), providers=["CPUExecutionProvider"])
    dummy = tokenizer(
        "warmup text for latency benchmark",
        return_tensors="np",
        max_length=512,
        truncation=True,
        padding="max_length",
    )
    feed = _normalize_onnx_feed(
        session,
        {key: val for key, val in dummy.items() if key in {i.name for i in session.get_inputs()}},
    )

    for _ in range(10):
        session.run(None, feed)

    latencies: list[float] = []
    for _ in range(100):
        start = time.perf_counter()
        session.run(None, feed)
        latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    p95 = latencies[94]

    size_mb = dest_onnx.stat().st_size / (1024 * 1024)
    result = ExportResult(
        model_path=str(dest_onnx),
        model_size_mb=round(size_mb, 2),
        sha256_hash=sha256,
        sample_latency_ms=round(p95, 3),
        injection_class_index=injection_index,
    )
    print("\n=== Export Complete ===")
    print(f"Model path:            {result.model_path}")
    print(f"Model size:            {result.model_size_mb} MB")
    print(f"Injection class index: {result.injection_class_index}")
    print(f"SHA-256:               {result.sha256_hash[:16]}...")
    print(f"P95 latency:           {result.sample_latency_ms} ms (CPU)")
    print(f"Quantized:             {quantize}")
    print("=======================\n")
    return result


def _write_scorer_metadata(models_dir: Path, injection_index: int) -> None:
    import json

    meta_path = models_dir / "scorer_config.json"
    meta_path.write_text(
        json.dumps({"injection_class_index": int(injection_index)}, indent=2) + "\n",
        encoding="utf-8",
    )


def _quantize_onnx_dynamic(model_path: Path) -> Path:
    """Apply ONNX Runtime dynamic INT8 quantization; return path to quantized model."""
    from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: PLC0415

    quantized = model_path.with_name("risk_scorer.int8.onnx")
    quantize_dynamic(
        model_input=str(model_path),
        model_output=str(quantized),
        weight_type=QuantType.QUInt8,
    )
    model_path.unlink(missing_ok=True)
    quantized.replace(model_path)
    print(f"Dynamic INT8 quantization written to {model_path}")
    return model_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export AgentGuard ONNX risk scorer")
    parser.add_argument("--checkpoint", default="training/checkpoints/best")
    parser.add_argument("--output-dir", default="agentguard/models")
    parser.add_argument("--data-dir", default="training/data")
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Apply ONNX Runtime dynamic INT8 quantization after export",
    )
    cli = parser.parse_args()
    export_to_onnx(
        cli.checkpoint,
        cli.output_dir,
        quantize=cli.quantize,
        data_dir=cli.data_dir,
    )
