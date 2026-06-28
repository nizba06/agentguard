# AgentGuard

Inter-agent security firewall for multi-agent AI systems (LangGraph, CrewAI, AutoGen).

AgentGuard intercepts every message between agents and enforces three runtime controls:

1. **Message Inspector** — Aho-Corasick rule filter + DeBERTa ML scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 signing via PyNaCl
3. **Capability Enforcer** — YAML manifests with JSON Schema validation and monotonic attenuation

## Quick start

```bash
# Python 3.11 or 3.12
pip install -e ".[all,otel]"
# or: poetry install --extras all --extras otel

agentguard status
agentguard check-manifest manifests/comms_agent.yaml
agentguard inspect -m "Summarise public pricing data from filings."
pytest
```

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

Anthropic Batch dataset generation (v1.0 novel corpus) is deferred — see [scripts/LAUNCH_CHECKLIST.md](scripts/LAUNCH_CHECKLIST.md).

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

For framework adapters in your own Dockerfile: `pip install "agentguard[all,otel]"`.

Optional OpenTelemetry export (requires `pip install agentguard[otel]`):

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

### Build dataset (zero cost)

```powershell
.\scripts\run_public_dataset_build.ps1
```

Sources: InjecAgent (GitHub) + inter-agent framing templates + pipeline-style benign messages.

### Run evaluation

```powershell
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

Results: `benchmarks/results/report.md`

### Latest results (2026-06-30 full run)

| Metric | Value |
|--------|-------|
| Overall detection rate | 97.1% |
| False positive rate | 0.0% |
| P95 inspection latency | ~1060 ms (CPU ONNX) |
| ML model loaded | Yes |

CPU latency exceeds the 15 ms design target; use GPU ONNX providers or async inspection for high-frequency pipelines.

### v1.0 launch

Novel dataset via Anthropic Batch API — see [scripts/LAUNCH_CHECKLIST.md](scripts/LAUNCH_CHECKLIST.md).

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
- [Blog draft](docs/BLOG_POST_DRAFT.md)
- [Release notes draft](docs/RELEASE_NOTES_v0.1.0-draft.md)
- [Launch checklist](scripts/LAUNCH_CHECKLIST.md)

## License

Apache-2.0 — see [LICENSE](LICENSE).
