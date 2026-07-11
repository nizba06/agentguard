# AgentGuard Launch Checklist & Launch Gap Analysis

Track everything required to ship **v0.1.0** and **v1.0** follow-ons.

---

## Launch gap summary

| Gap | Status | Action |
|-----|--------|--------|
| ONNX model + GitHub release | **Done** | https://github.com/nizba06/agentguard/releases/tag/v0.1.0 |
| PyPI publish | **Done** | `pip install inter-agent-guard` (import `agentguard`) |
| Code commit/push | **Done** | `origin/master` |
| Anthropic novel dataset (local) | **Done** | `benchmarks/dataset/*.jsonl` |
| Hugging Face dataset upload | **In progress** | `scripts/publish_huggingface.ps1` → `nizba06/agentguard-benchmark-v1.0` |
| Blog post | **Done** | `docs/BLOG_POST.md` |
| agentguard-demo on GitHub | **In progress** | PyPI dependency + public repo |
| P95 latency vs 15 ms | Documented | ~1060 ms CPU — known limitation |
| Sphinx API docs | Not started | v1.0 P1 |
| Microsoft toolkit comparison | Not started | REQUIREMENTS §12.3 |

**Bottom line:** Library v0.1.0 is published (PyPI + GitHub release + ONNX). Remaining: HF dataset publish and demo repo public release.

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
| Blog | **Done** | `docs/BLOG_POST.md` |
| Hugging Face dataset | Pending upload | Card ready |
| Demo repo | Pending first push | Uses PyPI package |

---

## Quick reference — scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify_release.ps1` | Pre-release lint/tests/smoke |
| `scripts/publish_pypi.ps1` | Publish `inter-agent-guard` |
| `scripts/create_github_release.ps1` | Tag + ONNX assets |
| `scripts/publish_huggingface.ps1` | Upload benchmark JSONL |
| `scripts/install_model.ps1` / `.sh` | Install ONNX locally |
