# AgentGuard

Inter-agent security firewall for multi-agent AI systems (LangGraph, CrewAI, AutoGen).

AgentGuard intercepts every message between agents and enforces three runtime controls:

1. **Message Inspector** — Aho-Corasick rule filter + DeBERTa ML scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 signing via PyNaCl
3. **Capability Enforcer** — YAML manifests with JSON Schema validation and monotonic attenuation

## Quick start

```bash
# Python 3.11 or 3.12
# PyPI distribution name (import package is still agentguard)
pip install "inter-agent-guard[all,otel]"
# from a clone: pip install -e ".[all,otel]"

agentguard status
agentguard check-manifest manifests/comms_agent.yaml
agentguard inspect -m "Summarise public pricing data from filings."
```

```python
from agentguard import AgentGuard, CapabilityManifest
```

Download `risk_scorer.onnx` + `model.sha256` from the [GitHub Releases](https://github.com/nizba06/agentguard/releases) page, install into the package `models/` directory (or pass `model_path=`), then set `require_ml_model=True` for production enforce-mode.

> **Note:** The PyPI project is `inter-agent-guard` because bare `agentguard` collides with existing `agent-guard` under PyPI’s name rules. The Python import and CLI remain `agentguard`.

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.75,
    task_objective="Analyse Q3 competitor pricing",
    audit_log_path="./audit.jsonl",
    # Set True in production after installing the ONNX model
    require_ml_model=False,
)
guard.register_agent(
    "research-agent",
    CapabilityManifest.from_yaml("manifests/research_agent.yaml"),
)
secured_graph = guard.wrap(my_langgraph_graph)
```

Without the ONNX model, rule filtering and trust attestation still run; ML scoring is inactive. For production enforce-mode, install the model (next section) and set `require_ml_model=True`.

## Production setup

1. **Install the ML model** (required for enforce-mode ML scoring):

   ```bash
   # Bash — after training or downloading artifacts
   ./scripts/install_model.sh ./path/to/model/dir
   python scripts/verify_model.py
   ```

   ```powershell
   # PowerShell
   .\scripts\install_model.ps1 -SourceDir .\path\to\model\dir
   py -3.12 scripts\verify_model.py
   ```

   Sources: local training (`./scripts/run_training.ps1 -Full`) or Kaggle download (`.\scripts\download_kaggle_model.ps1`).

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

CPU latency exceeds the 15 ms design target; use GPU ONNX providers or async inspection for high-frequency pipelines.

Reproduce with the HF corpus or local `benchmarks/dataset/*.jsonl` after `.\scripts\install_model.ps1`.

## Training (Kaggle GPU)

```powershell
.\scripts\push_kaggle_kernel.ps1   # uploads code dataset + pushes notebook
```

Open kernel on Kaggle → GPU T4 x2 + Internet → Run All. Copy `agentguard/models/*` from Output tab.

See [training/kaggle_notebook.ipynb](training/kaggle_notebook.ipynb).

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [REQUIREMENTS.md](docs/REQUIREMENTS.md)
- [DESIGN.md](docs/DESIGN.md)
- [Technical blog](docs/BLOG_POST.md)
- [Blog draft (archive)](docs/BLOG_POST_DRAFT.md)
- [Release notes](docs/RELEASE_NOTES_v0.1.0.md)
- [Launch checklist](scripts/LAUNCH_CHECKLIST.md)
- [Hugging Face dataset card](docs/HUGGINGFACE_DATASET_CARD.md)

## License

Apache-2.0 — see [LICENSE](LICENSE).
