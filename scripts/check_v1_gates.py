"""Fail if holdout (or optional full) benchmark report misses v1.0 gates.

Usage:
  py -3.12 scripts/check_v1_gates.py
  py -3.12 scripts/check_v1_gates.py --report benchmarks/results/holdout_report.md
  py -3.12 scripts/check_v1_gates.py --also-full
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DETECTION_MIN = 0.90
FPR_MAX = 0.03
# Soft latency gate: CPU may fail; require documented override via --allow-cpu-latency
P95_MS_MAX = 15.0
MODEL_MB_MAX = 180.0  # DeBERTa-v3-small dynamic INT8 (~170MB); FP32 ~540MB is not shippable


def _parse_metric(text: str, label: str) -> float | None:
    # | Overall detection rate | 6.2% |
    pattern = rf"\|\s*{re.escape(label)}\s*\|\s*([0-9.]+)\s*%?\s*\|"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _parse_detection_pct(text: str) -> float | None:
    raw = _parse_metric(text, "Overall detection rate")
    if raw is None:
        return None
    return raw / 100.0 if raw > 1.0 else raw


def _parse_fpr_pct(text: str) -> float | None:
    raw = _parse_metric(text, "False positive rate")
    if raw is None:
        return None
    return raw / 100.0 if raw > 1.0 else raw


def _parse_p95_ms(text: str) -> float | None:
    match = re.search(
        r"\|\s*P95 inspection latency\s*\|\s*([0-9.]+)\s*ms\s*\|",
        text,
        flags=re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def evaluate_report(
    path: Path,
    *,
    allow_cpu_latency: bool,
) -> list[str]:
    if not path.exists():
        return [f"Missing report: {path}"]
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    detection = _parse_detection_pct(text)
    fpr = _parse_fpr_pct(text)
    p95 = _parse_p95_ms(text)

    if detection is None:
        failures.append(f"{path}: could not parse overall detection rate")
    elif detection < DETECTION_MIN:
        failures.append(
            f"{path}: detection {detection:.1%} < {DETECTION_MIN:.0%} gate"
        )

    if fpr is None:
        failures.append(f"{path}: could not parse false positive rate")
    elif fpr > FPR_MAX:
        failures.append(f"{path}: FPR {fpr:.1%} > {FPR_MAX:.0%} gate")

    if p95 is None:
        failures.append(f"{path}: could not parse P95 latency")
    elif p95 > P95_MS_MAX and not allow_cpu_latency:
        failures.append(
            f"{path}: P95 {p95:.1f}ms > {P95_MS_MAX}ms "
            "(pass --allow-cpu-latency only with published GPU/async SLA)"
        )

    return failures


def check_model_size(model_path: Path) -> list[str]:
    if not model_path.exists():
        return [f"Missing ONNX model: {model_path}"]
    mb = model_path.stat().st_size / (1024 * 1024)
    if mb > MODEL_MB_MAX:
        return [f"ONNX size {mb:.1f} MB > {MODEL_MB_MAX:.0f} MB gate"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AgentGuard v1.0 release gates")
    parser.add_argument(
        "--report",
        default="benchmarks/results/holdout_report.md",
        help="Primary report (default: holdout)",
    )
    parser.add_argument(
        "--also-full",
        action="store_true",
        help="Also require full-corpus report.md to pass gates",
    )
    parser.add_argument(
        "--allow-cpu-latency",
        action="store_true",
        help="Skip CPU P95 < 15ms gate when GPU/async SLA is documented",
    )
    parser.add_argument(
        "--skip-model-size",
        action="store_true",
        help="Skip ONNX < 120MB gate (not recommended for 1.0)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    failures.extend(
        evaluate_report(root / args.report, allow_cpu_latency=args.allow_cpu_latency)
    )
    if args.also_full:
        failures.extend(
            evaluate_report(
                root / "benchmarks/results/report.md",
                allow_cpu_latency=args.allow_cpu_latency,
            )
        )
    if not args.skip_model_size:
        failures.extend(check_model_size(root / "agentguard/models/risk_scorer.onnx"))

    print("v1.0 gate check")
    print(f"  holdout report: {args.report}")
    print(f"  detection >= {DETECTION_MIN:.0%}")
    print(f"  FPR <= {FPR_MAX:.0%}")
    print(f"  P95 <= {P95_MS_MAX} ms (allow_cpu_latency={args.allow_cpu_latency})")
    print(f"  ONNX <= {MODEL_MB_MAX:.0f} MB INT8 (skip={args.skip_model_size})")

    if failures:
        print("\nFAIL:")
        for item in failures:
            print(f"  - {item}")
        print("\nDo not tag 1.0.0 until these clear. See docs/V1_ROADMAP.md.")
        return 1

    print("\nPASS: v1.0 gates cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
