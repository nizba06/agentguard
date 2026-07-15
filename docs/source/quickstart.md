# Quick start

```bash
pip install "inter-agent-guard[all,otel]"
python scripts/download_release_model.py   # ~164 MB INT8 ONNX from GitHub Releases
agentguard status
```

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.85,
    task_objective="Analyse Q3 competitor pricing",
    audit_log_path="./audit.jsonl",
    require_ml_model=True,  # after download_release_model.py
)
guard.register_agent(
    "research-agent",
    CapabilityManifest.from_yaml("manifests/research_agent.yaml"),
)
secured = guard.wrap(my_langgraph_graph)
```

Without the ONNX model, rule filtering, trust attestation, and capability
enforcement still run. Set `require_ml_model=True` only after the model is installed.

## Links

- **Docs:** https://inter-agent-guard.readthedocs.io/
- GitHub: https://github.com/nizba06/agentguard
- PyPI: https://pypi.org/project/inter-agent-guard/
- Demo: https://github.com/nizba06/inter-agent-guard-demo
- Dataset: https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1
