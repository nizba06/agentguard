# AgentGuard v0.1.0 — Release Notes (Draft)

**Status:** Production-ready codebase — install `risk_scorer.onnx` before enforce-mode deployment.

## Highlights

- Inter-agent security middleware for LangGraph, CrewAI, and AutoGen
- Three-layer defence: rule filter + DeBERTa ML scorer + consistency check
- Ed25519 trust attestation and YAML capability manifests with delegation attenuation
- MCP tool output inspection (`MCPPoisoningException`)
- Append-only hash-chained audit log + CLI verify
- Benchmark harness with attack-class-aware evaluation (6,200 public-source examples)

## Production checklist

1. Build dataset: `.\scripts\run_public_dataset_build.ps1`
2. Train or download model:
   - Kaggle: `.\scripts\download_kaggle_model.ps1` → `.\scripts\install_model.ps1`
   - Local: `.\scripts\run_training.ps1 -Full` (GPU recommended)
3. Verify: `py -3.12 scripts\verify_model.py`
4. Pre-release: `.\scripts\verify_release.ps1`
5. Full benchmark: `.\scripts\run_benchmark_evaluation.ps1 -RequireModel`
6. Demo: `poetry run python examples/secured_pipeline/pipeline.py`

Anthropic Batch novel dataset generation is deferred to v1.0 launch — see `scripts/LAUNCH_CHECKLIST.md`.

## Benchmark results (public-source corpus, 2026-06-30)

| Metric | Value |
|--------|-------|
| Overall detection rate | 97.1% |
| False positive rate | 0.0% |
| P95 inspection latency | 1059.9 ms (CPU) |

Per attack class: INDIRECT_INJECTION 95%, MCP_POISONING 93%, PROPAGATION 94.5%; others 100%. Full report: `benchmarks/results/report.md`.

## Test results

- ~90 tests passing
- >85% line coverage (enforced in CI)

## Known limitations

- DeBERTa fine-tuning on CPU is impractically slow; use Kaggle GPU or local CUDA
- Full CPU benchmark over 6,200 examples is slow (~1–2 hours with ML model loaded)
- ONNX model shipped separately (GitHub release artifact), not in PyPI wheel
- v0.1 dataset uses public-source derivation; v1.0 adds Anthropic-generated novel corpus
- Anthropic API is used only for offline dataset generation, not at runtime
