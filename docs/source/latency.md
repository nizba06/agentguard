# Latency and deployment modes

AgentGuard’s design target was **P95 ≤ 15 ms** for inspection. Measured
CPU ONNX P95 on the Anthropic v1.0 corpus is on the order of **~0.8–1.1 s**
per message. Use the modes below to match your pipeline’s latency budget.

## Mode matrix

| Mode | ML ONNX | Blocking | Typical use |
|------|---------|----------|-------------|
| **Rules-only** | Off | Yes | Fast path; pattern + capability + trust |
| **Monitor** | Optional | No (audit only) | Shadow deploy; collect FPs before enforce |
| **Enforce + ML (CPU)** | On | Yes | Highest detection; accept ~1 s P95 |
| **Enforce + ML (GPU)** | On (CUDA EP) | Yes | Lower ML latency when CUDA available |
| **Async / eventual** | On | Deferred | Deliver first; quarantine on late high risk |

## Rules-only (lowest latency)

Omit the ONNX file and keep `require_ml_model=False` (default). Rule filter,
Ed25519 trust, and capability manifests still run — usually well under
the ML path.

```python
guard = AgentGuard(
    require_ml_model=False,
    mode="enforce",
    audit_log_path="./audit.jsonl",
)
```

## Monitor-only (zero blocking)

```python
guard = AgentGuard(mode="monitor", require_ml_model=True, audit_log_path="./audit.jsonl")
```

Decisions are logged; messages and tool calls are not blocked. Use this to
measure false positives on production traffic before switching to `enforce`.

## GPU ONNX

`MLRiskScorer` prefers `CUDAExecutionProvider` when onnxruntime reports it,
otherwise CPU. Install a CUDA build of onnxruntime (or `onnxruntime-gpu`)
and ensure drivers match your ORT version.

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
python scripts/download_release_model.py
```

## Async / high-frequency pipelines

For chatty multi-agent graphs where ~1 s synchronous inspection is too slow:

1. Run **rules-only** (or monitor) on the hot path.
2. Offload ML scoring to a worker queue; quarantine or page on high risk.
3. Cap which hops call `inspect_message` (e.g. tool-return and external-facing agents only).

Adapters already wrap async LangGraph node functions; keep ML off the
critical path until GPU or async inspection is in place.

## Benchmark tip

```powershell
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

See `benchmarks/results/report.md` for the latest P95 figures.
