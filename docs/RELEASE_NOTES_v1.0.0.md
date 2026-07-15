# inter-agent-guard v1.0.0 — Release Notes

**Released:** 2026-07-15  
**PyPI:** `inter-agent-guard` · **Import:** `agentguard`  
**Repo:** https://github.com/nizba06/agentguard  
**Docs:** https://inter-agent-guard.readthedocs.io/

## Highlights

- **Holdout gates cleared** (20% Anthropic carve-out, 160 adversarial + 1,000 benign):
  - Detection **99.4%**, FPR **0.0%**
  - ML layer catches ~95% of content attacks; rules catch the rest of detected cases
- Default ONNX artifact is **dynamic INT8** (~164 MB, SHA-256 pinned)
- Ship tooling: `scripts/check_v1_gates.py`, `scripts/ship_v1.ps1`, `run_benchmark_evaluation.ps1 -Holdout`
- Deterministic layers (capability / impersonation / trust) unchanged and production-ready

## Install

```bash
pip install "inter-agent-guard==1.0.0"
# Download risk_scorer.onnx + model.sha256 from GitHub Releases into agentguard/models/
python scripts/verify_model.py   # from a checkout, or use install_model helpers
```

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.85,
    require_ml_model=True,
    task_objective="Analyse Q3 competitor pricing",
)
```

### ML model (required for enforce-mode scoring)

| Artifact | Notes |
|----------|-------|
| `risk_scorer.onnx` | Dynamic INT8 (~164 MB); SHA-256 `1f758299994793a033153c27a033eb998c5e37090d51da3ce0af1c4807fe6894` |
| `tokenizer.json` / `tokenizer_config.json` | Bundled in the wheel under `agentguard/models/` |

## Latency SLA (honest)

CPU ONNX P95 on holdout is **~3 s**, not the original 15 ms design target. For high-QPS production:

- **Rules-only** / capability / trust (no ONNX)
- **GPU** ONNX Execution Provider
- **Async / monitor** modes — see `docs/source/latency.md`

v1.0 explicitly documents this CPU exception; do not assume sub-15 ms on CPU with ML enabled.

## Benchmark authority

**Holdout** (`benchmarks/results/holdout_report.md`) is the ship gate. Full-corpus scores can overstate quality when the scorer trained on that JSONL.

Dataset: https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1

## Verify gates locally

```powershell
py -3.12 scripts/verify_model.py
.\scripts\run_benchmark_evaluation.ps1 -Holdout -RequireModel
py -3.12 scripts/check_v1_gates.py --allow-cpu-latency
```
