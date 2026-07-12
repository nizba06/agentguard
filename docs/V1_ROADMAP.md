# AgentGuard v1.0 Roadmap

Gates for tagging **v1.0.0** (Anthropic corpus or holdout split):

| Gate | Target |
|------|--------|
| Overall detection | > 90% |
| False positive rate | < 3% |
| P95 latency (CPU) **or** published GPU/async SLA | < 15 ms CPU preferred |
| Deterministic layers (impersonation, capability) | 100% |

## Phase status

### Phase 1 — ML quality (in progress)

- [x] Anthropic-primary `training/prepare_dataset.py` (`--source anthropic`)
- [x] 20% holdout under `benchmarks/dataset/holdout/`
- [x] `scripts/retrain_checklist.ps1`
- [ ] Full DeBERTa fine-tune on Kaggle GPU (or local CUDA)
- [ ] Export + pin ONNX (`training/export_onnx.py`)
- [ ] Holdout + full-corpus eval clears detection/FPR gates

```powershell
.\scripts\retrain_checklist.ps1 -Prepare
.\scripts\push_kaggle_kernel.ps1   # preferred for full train
# after pulling checkpoint:
py -3.12 training/export_onnx.py --quantize
py -3.12 scripts/verify_model.py
.\scripts\retrain_checklist.ps1 -EvaluateHoldout
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

### Phase 2 — Consistency FPR

- [x] Raise default `consistency_ml_risk_floor` to **0.75** (gray band only)
- [ ] Ablate `enable_consistency_check=False` on holdout after new ML lands
- [ ] Keep or drop consistency based on ablation

### Phase 3 — Latency

- [x] `--stage-timing-sample N` on `benchmarks/evaluate.py`
- [x] `--quantize` dynamic INT8 path on `training/export_onnx.py`
- [ ] Measure quantized CPU P95; document GPU/async if CPU cannot hit 15 ms

```powershell
py -3.12 benchmarks/evaluate.py --quick --require-ml-model --stage-timing-sample 40
```

### Phase 4 — Ship

- [x] v0.1.1 hygiene released (firewall split, async MCP, honest NFRs)
- [ ] When gates pass: bump to 1.0.0, PyPI, GitHub Release + ONNX, README/blog/HF card

## Honest constraint

Phase 1 full retrain needs a **GPU** (Kaggle free tier is the project default). CPU smoke
train (`--quick`) validates the pipeline only — it is not a 1.0 model.
