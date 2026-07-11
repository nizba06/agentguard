# AgentGuard

Inter-agent security firewall for multi-agent AI systems (LangGraph, CrewAI, AutoGen).

**PyPI:** `pip install inter-agent-guard` · **Import / CLI:** `agentguard`  
**Docs:** [docs/](docs/) · [Blog post](docs/BLOG_POST.md) · [Demo](https://github.com/nizba06/inter-agent-guard-demo)

AgentGuard intercepts every message between agents and enforces three runtime controls:

1. **Message Inspector** — Aho-Corasick rule filter + DeBERTa ML scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 signing via PyNaCl
3. **Capability Enforcer** — YAML manifests with JSON Schema validation and monotonic attenuation

## Quick start

```bash
# Python 3.11 or 3.12
pip install "inter-agent-guard[all,otel]"
# ONNX weights are not in the wheel (~540 MB) — from a clone:
python scripts/download_release_model.py
# or: download risk_scorer.onnx + model.sha256 from GitHub Releases into agentguard/models/

agentguard status
agentguard check-manifest manifests/comms_agent.yaml
agentguard inspect -m "Summarise public pricing data from filings."
```

> **Note:** The PyPI project is `inter-agent-guard` because bare `agentguard` collides with existing `agent-guard` under PyPI’s name rules. The Python import and CLI remain `agentguard`.

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.75,
    task_objective="Analyse Q3 competitor pricing",
    audit_log_path="./audit.jsonl",
    # Set True in production after installing the ONNX model
    require_ml_model=True,
)
guard.register_agent(
    "research-agent",
    CapabilityManifest.from_yaml("manifests/research_agent.yaml"),
)
secured_graph = guard.wrap(my_langgraph_graph)
```

Without the ONNX model, rule filtering and trust attestation still run; ML scoring is inactive.

## Latency and deployment modes

CPU ONNX P95 is ~0.8–1.1 s (design target was 15 ms). Choose a mode that fits your budget:

| Mode | How | When |
|------|-----|------|
| **Rules-only** | `require_ml_model=False` (no ONNX) | Lowest latency; patterns + capability + trust |
| **Monitor** | `mode="monitor"` | Shadow deploy; audit without blocking |
| **Enforce + ML (CPU)** | `require_ml_model=True` | Highest detection; accept ~1 s P95 |
| **Enforce + ML (GPU)** | Install `onnxruntime-gpu` | Lower ML latency when CUDA is available |
| **Async / selective hops** | Rules on hot path; ML off-path | High-frequency graphs |

Full guide: [docs/source/latency.md](docs/source/latency.md).

## Production setup

1. **Install the ML model** (required for enforce-mode ML scoring):

   ```bash
   python scripts/download_release_model.py
   python scripts/verify_model.py
   ```

   ```powershell
   py -3.12 scripts\download_release_model.py
   py -3.12 scripts\verify_model.py
   ```

   Or copy artifacts you already have:

   ```bash
   ./scripts/install_model.sh ./path/to/model/dir
   # PowerShell: .\scripts\install_model.ps1 -SourceDir .\path\to\model\dir
   ```

   Sources: [GitHub Releases v0.1.0](https://github.com/nizba06/agentguard/releases/tag/v0.1.0), local training, or Kaggle (`.\scripts\download_kaggle_model.ps1`).

2. **Confirm health**:

   ```bash
   agentguard status
   ```

3. **Optional — build benchmark dataset** (no API key):

   ```powershell
   .\scripts\run_public_dataset_build.ps1
   .\scripts\run_benchmark_evaluation.ps1 -RequireModel
   ```

4. **Run secured demo**:

   ```bash
   poetry run python examples/secured_pipeline/pipeline.py
   ```

Novel v1.0 corpus is on [Hugging Face](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1). To regenerate locally, see [docs/ANTHROPIC_DATASET_RUNBOOK.md](docs/ANTHROPIC_DATASET_RUNBOOK.md).

### CLI

```bash
agentguard version
agentguard status [--json]
agentguard check-manifest manifests/comms_agent.yaml [--json]
agentguard inspect -m "message text" [--json]
agentguard verify ./audit.jsonl [--json]
```

### Docker

Core runtime image (firewall + OTEL; LangGraph/CrewAI/AutoGen installed separately in app images):

```bash
docker build -t agentguard .
docker run --rm agentguard
docker run --rm -v "%CD%\audit.jsonl:/data/audit.jsonl" agentguard verify /data/audit.jsonl
```

For framework adapters in your own Dockerfile: `pip install "inter-agent-guard[all,otel]"`.

Optional OpenTelemetry export (requires `pip install "inter-agent-guard[otel]"`):

```python
guard = AgentGuard(enable_otel_export=True, audit_log_path="./audit.jsonl")
```

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to auto-configure the OTLP exporter.

## Capability enforcement

Manifests declare tools, data sources, endpoints, token limits, and delegation. At runtime:

| API | Enforces |
|-----|----------|
| `check_tool_call(agent, tool, endpoint=...)` | `permitted_tools`, `forbidden_tools`, optional `permitted_endpoints` |
| `check_endpoint(agent, url)` | `external_contact` + `permitted_endpoints` |
| `check_data_source(agent, source)` | `allowed_data_sources` |
| `check_output_tokens(agent, n)` | `max_output_tokens` |
| `register_delegated_agent(...)` | `can_spawn_agents`, `max_delegation_depth`, monotonic attenuation |

See example manifests under `manifests/` (including `comms_agent.yaml` with endpoint allowlists).

## Examples

```bash
# Vulnerable baseline (100% attack success)
poetry run python examples/vulnerable_pipeline/pipeline.py

# AgentGuard-protected version
poetry run python examples/secured_pipeline/pipeline.py

# MCP poisoning, CrewAI, AutoGen
poetry run python examples/mcp_poisoning_demo.py
poetry run python examples/crewai_example.py
poetry run python examples/autogen_example.py
```

## Benchmark

AgentGuard ships with a 6,200-example inter-agent benchmark (1,200 adversarial + 5,000 benign).

**Published on Hugging Face:** [Nizba/agentguard-benchmark-v1](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1) (Anthropic Batch, `anthropic_batch_v1`).

### Build dataset locally (zero cost, optional)

```powershell
.\scripts\run_public_dataset_build.ps1
```

Sources: InjecAgent (GitHub) + inter-agent framing templates + pipeline-style benign messages.

### Run evaluation

```powershell
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

Results: `benchmarks/results/report.md`

### Latest results (Anthropic v1.0 corpus)

| Metric | Value |
|--------|-------|
| Overall detection rate | 40.2% |
| False positive rate | 42.2% |
| P95 inspection latency | ~805 ms (CPU ONNX) |
| ML model loaded | Yes |

See [latency modes](#latency-and-deployment-modes) for production trade-offs.

Reproduce with the HF corpus or local `benchmarks/dataset/*.jsonl` after `python scripts/download_release_model.py`.

### vs Microsoft Agent Governance Toolkit

Feature matrix and shared-dataset methodology: [docs/MICROSOFT_TOOLKIT_COMPARISON.md](docs/MICROSOFT_TOOLKIT_COMPARISON.md).

```powershell
py -3.12 scripts\run_toolkit_comparison.py
```

## Training (Kaggle GPU)

```powershell
.\scripts\push_kaggle_kernel.ps1   # uploads code dataset + pushes notebook
```

Open kernel on Kaggle → GPU T4 x2 + Internet → Run All. Copy `agentguard/models/*` from Output tab.

See [training/kaggle_notebook.ipynb](training/kaggle_notebook.ipynb).

## Documentation

- [Sphinx API docs](docs/source/) — build with `poetry install --with docs && sphinx-build -b html docs/source docs/_build/html`
- [Technical blog](docs/BLOG_POST.md)
- [Microsoft toolkit comparison](docs/MICROSOFT_TOOLKIT_COMPARISON.md)
- [Latency / deployment modes](docs/source/latency.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [REQUIREMENTS.md](docs/REQUIREMENTS.md)
- [DESIGN.md](docs/DESIGN.md)
- [Release notes](docs/RELEASE_NOTES_v0.1.0.md)
- [Launch checklist](scripts/LAUNCH_CHECKLIST.md)
- [Hugging Face dataset card](docs/HUGGINGFACE_DATASET_CARD.md)

Build docs locally:

```bash
poetry install --with docs
sphinx-build -b html docs/source docs/_build/html
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
