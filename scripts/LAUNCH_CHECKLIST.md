# AgentGuard Launch Checklist & Launch Gap Analysis

Track everything required to ship **v0.1.0** and **v1.0** follow-ons.

---

## Launch gap summary

| Gap | Status | Action |
|-----|--------|--------|
| ONNX model + GitHub release | **Done** | https://github.com/nizba06/agentguard/releases/tag/v0.1.0 |
| Public GitHub repo | **Done** | https://github.com/nizba06/agentguard (public) |
| Public ONNX download | **Done** | `scripts/download_release_model.py` (anonymous HTTPS) |
| PyPI publish | **Done** | `pip install inter-agent-guard` (import `agentguard`) |
| Code commit/push | **Done** | `origin/master` |
| Anthropic novel dataset (local) | **Done** | `benchmarks/dataset/*.jsonl` |
| Hugging Face dataset upload | **Done** | https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1 |
| Blog post | **Done** | [docs/BLOG_POST.md](../docs/BLOG_POST.md) (public repo) |
| inter-agent-guard-demo | **Done** | https://github.com/nizba06/inter-agent-guard-demo |
| P95 latency vs 15 ms | **Documented** | [docs/source/latency.md](../docs/source/latency.md) — rules-only / monitor / GPU / async |
| Sphinx API docs | **Done** | `docs/source/` + `.readthedocs.yaml` |
| Microsoft toolkit comparison | **Done** | [docs/MICROSOFT_TOOLKIT_COMPARISON.md](../docs/MICROSOFT_TOOLKIT_COMPARISON.md) |
| Holdout as ship gate | **Done** | `run_benchmark_evaluation.ps1 -Holdout` + `check_v1_gates.py` |
| v1.0.0 tag | **Ready to publish** | Gates PASS (99.4% / 0% FPR INT8); commit + tag + PyPI + Release ONNX |

**Bottom line:** Library **1.0.0** clears holdout gates with INT8 ONNX. Operator steps remaining: git tag, PyPI upload, GitHub Release attach `risk_scorer.onnx` + `model.sha256`. See [docs/V1_ROADMAP.md](../docs/V1_ROADMAP.md).

---

## Release readiness matrix

| Area | Status | Notes |
|------|--------|-------|
| Firewall / trust / capability / MCP | **Done** | |
| Adapters + audit CLI + OTEL | **Done** | |
| Tests + CI + Docker | **Done** | |
| LICENSE + CONTRIBUTING | **Done** | |
| PyPI `inter-agent-guard` 0.1.0 | **Done** | |
| GitHub release + ONNX | **Done** | `inter-agent-guard v0.1.0` |
| Repo visibility | **Done** | Public |
| Blog | **Done** | `docs/BLOG_POST.md` |
| Hugging Face dataset | **Done** | [Nizba/agentguard-benchmark-v1](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1) |
| Demo repo | **Done** | Public + ONNX installer |
| Sphinx / Read the Docs | **Done** | Import project on RTD once |
| vs Microsoft AGT | **Done** | Positioning + sample harness |

---

## Quick reference — scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify_release.ps1` | Pre-release lint/tests/smoke |
| `scripts/publish_pypi.ps1` | Publish `inter-agent-guard` |
| `scripts/create_github_release.ps1` | Tag + ONNX assets |
| `scripts/download_release_model.py` | Public ONNX install into package `models/` |
| `scripts/publish_huggingface.ps1` | Upload benchmark JSONL |
| `scripts/install_model.ps1` / `.sh` | Install ONNX from a local directory |
| `scripts/run_toolkit_comparison.py` | AgentGuard vs AGT sample positioning |
