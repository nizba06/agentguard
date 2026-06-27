# AgentGuard

Inter-agent security firewall for multi-agent AI systems (LangGraph, CrewAI, AutoGen).

AgentGuard intercepts every message between agents and enforces three runtime controls:

1. **Message Inspector** — Aho-Corasick rule filter + DeBERTa ML scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 signing via PyNaCl
3. **Capability Enforcer** — YAML manifests with JSON Schema validation and monotonic attenuation

## Quick start

```bash
poetry install
poetry run pytest
```

Copy trained artifacts from Kaggle into `agentguard/models/` (`risk_scorer.onnx`, `model.sha256`, tokenizer files), then verify:

```bash
py -3.12 scripts/verify_model.py
```

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.75,
    task_objective="Analyse Q3 competitor pricing",
    audit_log_path="./audit.jsonl",
    require_ml_model=True,
)
guard.register_agent("research-agent", CapabilityManifest.from_yaml("manifests/research_agent.yaml"))
secured_graph = guard.wrap(my_langgraph_graph)
```

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
.\scripts\run_benchmark_evaluation.ps1
```

Results: `benchmarks/results/report.md`

### Latest results (pending full run)

| Metric | Value |
|--------|-------|
| Overall detection rate | _see report.md_ |
| False positive rate | _see report.md_ |
| P95 inspection latency | _see report.md_ |
| ML model loaded | Yes (when `risk_scorer.onnx` present) |

Monitor progress: `py -3.12 -c "print(sum(1 for _ in open('benchmarks/results/benchmark_audit.jsonl')))"` → target **6200**.

### v1.0 launch

Novel dataset via Anthropic Batch API — see [scripts/LAUNCH_CHECKLIST.md](scripts/LAUNCH_CHECKLIST.md).

## Training (Kaggle GPU)

```powershell
.\scripts\push_kaggle_kernel.ps1   # uploads code dataset + pushes notebook
```

Open kernel on Kaggle → GPU T4 x2 + Internet → Run All. Copy `agentguard/models/*` from Output tab.

See [training/kaggle_notebook.ipynb](training/kaggle_notebook.ipynb).

## Documentation

- [REQUIREMENTS.md](docs/REQUIREMENTS.md)
- [DESIGN.md](docs/DESIGN.md)
- [Blog draft](docs/BLOG_POST_DRAFT.md)
- [Release notes draft](docs/RELEASE_NOTES_v0.1.0-draft.md)
- [Launch checklist](scripts/LAUNCH_CHECKLIST.md)

## License

Apache-2.0
