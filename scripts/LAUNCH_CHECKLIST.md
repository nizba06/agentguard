# AgentGuard Launch Checklist & Launch Gap Analysis

Track everything required to ship **v0.1.0** (library + public-source benchmark) and **v1.0** (novel Anthropic dataset + full REQUIREMENTS §12).

---

## Launch gap summary

| Gap | Blocks v0.1.0? | Blocks v1.0? | Owner / action |
|-----|----------------|----------------|----------------|
| ONNX model not in repo (`risk_scorer.onnx`) | **Yes** (enforce-mode) | Yes | Train/download → `scripts/install_model.ps1` |
| ~1,400 lines uncommitted locally | **Yes** | Yes | Commit + push to `origin/master` |
| PyPI not published | **Yes** | Yes | `scripts/publish_pypi.ps1` + `PYPI_TOKEN` |
| GitHub release + ONNX artifact | **Yes** | Yes | Tag + attach `risk_scorer.onnx` + SHA-256 |
| Manifest schema pip path | ~~Yes~~ **Fixed** | — | Bundled in `agentguard/schemas/` |
| Anthropic novel dataset | No | **Yes** | `scripts/run_dataset_generation.ps1` (~$15–40) |
| Hugging Face dataset upload | No | **Yes** | `docs/HUGGINGFACE_DATASET_CARD.md` |
| Blog post with final metrics | No | Recommended | `docs/BLOG_POST_DRAFT.md` |
| P95 latency vs 15 ms design target | No (document) | No | ~1060 ms CPU — known limitation |
| Sphinx API docs | No | P1 | Not started |
| Microsoft toolkit comparison | No | P1 | REQUIREMENTS §12.3 — not implemented |

**Bottom line:** Code and tests are ready. **v0.1.0 is blocked by model install, commit/push, and distribution (PyPI + GitHub release).** **v1.0 adds the Anthropic novel corpus and Hugging Face publish.**

---

## Release readiness matrix

| Area | Status | Notes |
|------|--------|-------|
| Firewall (rules + ML + consistency) | **Done** | `agentguard/firewall.py` |
| Trust attestation (Ed25519) | **Done** | `agentguard/trust/` |
| Capability manifests + enforcement | **Done** | Tools, endpoints, data sources, tokens, spawn/depth |
| MCP output inspection | **Done** | `agentguard/mcp/` |
| Framework adapters (LangGraph, CrewAI, AutoGen) | **Done** | Optional extras |
| Audit log + CLI | **Done** | `verify`, `status`, `check-manifest`, `inspect` |
| OTEL export | **Done** | `[otel]` extra |
| Tests + coverage gate (>85%) | **Done** | ~89 tests |
| CI (ruff, mypy, pytest, benchmark smoke) | **Done** | `.github/workflows/ci.yml` |
| Docker image | **Done** | `Dockerfile` |
| LICENSE + CONTRIBUTING | **Done** | Apache-2.0 |
| Public-source benchmark | **Done** | 97.1% detection, 0% FPR |
| ONNX model in tree | **Missing** | Gitignored; install separately |
| PyPI publish | **Not done** | `scripts/publish_pypi.ps1` |
| GitHub v0.1.0 / v1.0 release | **Not done** | |
| Anthropic novel dataset | **Deferred v1.0** | Not used at runtime |
| Hugging Face dataset | **Not done** | |
| Technical blog | **Draft only** | Metrics need refresh |

---

## v0.1.0 release runbook (do in order)

### Step 1 — Install production ML model

Production enforce-mode requires `agentguard/models/risk_scorer.onnx`:

```powershell
# Option A: Kaggle GPU training output
.\scripts\download_kaggle_model.ps1
.\scripts\install_model.ps1 -SourceDir .\kaggle-model-pull\agentguard\models

# Option B: Local training (GPU recommended)
.\scripts\run_training.ps1 -Full
.\scripts\install_model.ps1 -SourceDir .\agentguard\models

# Verify hash + sample scores
py -3.12 scripts\verify_model.py
```

### Step 2 — Local pre-release verification

```powershell
.\scripts\verify_release.ps1

# Full benchmark (slow, ~1–2 h CPU with model)
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

Expected metrics (public-source corpus, 2026-06-30): **97.1% detection, 0% FPR**. See `benchmarks/results/report.md`.

### Step 3 — Commit and push

```powershell
git add -A
git status   # review: exclude local audit.jsonl, kaggle scratch dirs
git commit -m "Prepare AgentGuard v0.1.0 release"
git push origin master
```

Confirm GitHub Actions green on Python 3.11 and 3.12.

### Step 4 — PyPI publish

```powershell
$env:PYPI_TOKEN = "pypi-..."
.\scripts\publish_pypi.ps1
pip install agentguard   # smoke test in clean venv
```

### Step 5 — GitHub release

1. Tag: `git tag v0.1.0 && git push origin v0.1.0`
2. Create release from `docs/RELEASE_NOTES_v0.1.0-draft.md`
3. Attach release artifacts:
   - `agentguard/models/risk_scorer.onnx`
   - `agentguard/models/model.sha256`
   - SHA-256 of ONNX file in release notes

### Step 6 — Integration demo

Update `agentguard-demo` to reference PyPI version once published (replace path dependency).

---

## v1.0 launch gap (REQUIREMENTS §12.3)

These items are **explicitly deferred** from v0.1.0:

### Anthropic Batch novel dataset (~$15–35, one-time)

**Full runbook:** [docs/ANTHROPIC_DATASET_RUNBOOK.md](../docs/ANTHROPIC_DATASET_RUNBOOK.md)

The generator submits **one Batch job** (~185 chunked requests). It validates exact counts before saving.

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.\scripts\run_dataset_generation.ps1 -DryRun    # free pre-flight
.\scripts\run_dataset_generation.ps1            # single batch run (~30-120 min)
# If validation fails (rare):
.\scripts\run_dataset_generation.ps1 -TopUp     # fill deficits only
```

3. Re-run evaluation:
   ```powershell
   .\scripts\run_benchmark_evaluation.ps1 -RequireModel
   ```

4. Publish to Hugging Face:
   - Upload `benchmarks/dataset/adversarial.jsonl` and `benign.jsonl`
   - Dataset card: `docs/HUGGINGFACE_DATASET_CARD.md`

5. Update `benchmarks/dataset/README.md` provenance section.

### Until v1.0 — use zero-cost public-source builder

```powershell
.\scripts\run_public_dataset_build.ps1
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

### Other v1.0 items

- [ ] Technical blog — `docs/BLOG_POST_DRAFT.md` (fill metrics from `benchmarks/results/report.md`)
- [ ] Hugging Face dataset card finalized
- [ ] Microsoft Agent Governance Toolkit comparison (REQUIREMENTS §12.3)
- [ ] Multi-scale latency study (3/6/10/20 agents)
- [ ] Sphinx API reference (REQUIREMENTS §12.2)

---

## ML model tuning notes

Default consistency settings (`consistency_threshold=0.10`, `consistency_ml_risk_floor=0.15`) avoid quarantining low-risk pipeline traffic. Tune both when deploying with a strict task objective.

---

## Known limitations (document in release)

- CPU P95 inspection latency ~1060 ms (design target was 15 ms) — DeBERTa on CPU
- ONNX model not bundled in PyPI wheel (size); download from GitHub release or train locally
- v0.1 dataset is public-source derivation; v1.0 adds Anthropic-generated novel corpus
- Anthropic is **never** called at runtime — only for optional offline dataset generation

---

## Quick reference — scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify_release.ps1` | Pre-release: lint, mypy, pytest, benchmark smoke, optional model verify |
| `scripts/verify_model.py` | ONNX hash + injection/benign score checks |
| `scripts/install_model.ps1` | Copy model artifacts into `agentguard/models/` |
| `scripts/run_training.ps1` | Train + export ONNX |
| `scripts/download_kaggle_model.ps1` | Pull Kaggle kernel output |
| `scripts/publish_pypi.ps1` | Publish to PyPI |
| `scripts/run_dataset_generation.ps1` | Anthropic Batch dataset (v1.0) |
| `scripts/run_public_dataset_build.ps1` | Free public-source dataset (v0.1) |
| `scripts/run_benchmark_evaluation.ps1` | Full benchmark evaluation |
