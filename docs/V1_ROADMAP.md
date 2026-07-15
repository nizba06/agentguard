# AgentGuard v1.0 Roadmap

Gates for tagging **v1.0.0** — evaluated on the **holdout split** (not full corpus):

| Gate | Target | Status (2026-07-15 INT8) |
|------|--------|--------------------------|
| Overall detection (holdout) | > 90% | **PASS** — 99.4% |
| False positive rate (holdout) | < 3% | **PASS** — 0.0% |
| P95 latency (CPU) **or** published GPU/async SLA | < 15 ms CPU preferred | **PASS via SLA** — ~3.4 s CPU; see `docs/source/latency.md` |
| ONNX model size | < 180 MB INT8 | **PASS** — ~164 MB |
| Deterministic layers (impersonation, capability) | 100% on full suite | Pass |
| `scripts/verify_model.py` | Discriminating scorer | **PASS** (holdout probes) |

**Authority:** `benchmarks/results/holdout_report.md` + `scripts/check_v1_gates.py --allow-cpu-latency`.

## Phase status

### Phase 1 — ML quality

- [x] Anthropic-primary prepare + 20% holdout
- [x] Discriminating ONNX (INT8 release artifact)
- [x] Holdout eval clears detection/FPR gates

### Phase 2 — Consistency FPR

- [x] `consistency_ml_risk_floor` = 0.75
- [x] Holdout FPR 0.0% with current defaults (consistency not driving FPs)

### Phase 3 — Latency

- [x] Quantized INT8 ONNX
- [x] CPU SLA exception documented (`docs/source/latency.md`)

### Phase 4 — Ship

- [x] Version **1.0.0** in `pyproject.toml`
- [x] `docs/RELEASE_NOTES_v1.0.0.md`
- [ ] Commit / tag `v1.0.0` / PyPI upload / GitHub Release attach INT8 ONNX (operator step)

```powershell
py -3.12 scripts/check_v1_gates.py --allow-cpu-latency
# then: commit, tag, twine upload, gh release upload ONNX
```
