# AgentGuard: An Open-Source Firewall for Multi-Agent AI Systems

*Published: 2026-07-11 · [GitHub](https://github.com/nizba06/agentguard) · [PyPI](https://pypi.org/project/inter-agent-guard/) · [Demo](https://github.com/nizba06/inter-agent-guard-demo)*

Multi-agent systems trust messages between specialists — orchestrator, researcher, writer — without verifying content. One poisoned hop can hijack the entire pipeline. AgentGuard is a pip-installable Python middleware that inspects every inter-agent message at runtime.

**Install:** `pip install inter-agent-guard` (import as `agentguard`)  
**Repo:** https://github.com/nizba06/agentguard (public)  
**Docs:** https://github.com/nizba06/agentguard/tree/master/docs

## Problem

- Indirect injection in tool output and inter-agent messages
- Propagation across agent hops (LangGraph, CrewAI, AutoGen)
- Capability escalation and MCP tool-return poisoning
- Few public benchmarks aimed at *inter-agent* injection specifically

## Solution

Three runtime layers:

1. **Message Inspector** — Aho-Corasick rules + DeBERTa ONNX scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 per-agent signing (PyNaCl)
3. **Capability Enforcer** — YAML manifests (tools, endpoints, data sources, tokens, delegation) with monotonic attenuation

Plus **MCP output inspection** for tool-return poisoning.

## Demo

```bash
py -3.12 examples/vulnerable_pipeline/pipeline.py   # ATTACK SUCCEEDED
py -3.12 examples/secured_pipeline/pipeline.py      # ATTACK BLOCKED
```

## Benchmark results (Anthropic v1.0 corpus)

| Metric | Value |
|--------|-------|
| Overall detection rate | 40.2% |
| False positive rate | 42.2% |
| P95 inspection latency | ~805 ms (CPU ONNX) |
| Adversarial examples | 1,200 |
| Benign examples | 5,000 |

### Detection by attack class

| Attack class | Detection rate |
|--------------|----------------|
| CAPABILITY_ESCALATION | 100% |
| IMPERSONATION | 100% |
| GOAL_HIJACK | 17% |
| INDIRECT_INJECTION | 11% |
| MCP_POISONING | 9.5% |
| PROPAGATION | 4% |

CPU latency exceeds the 15 ms design target; use GPU ONNX providers or async inspection for high-frequency traffic.

On this novel Anthropic corpus, manifest/capability and trust layers catch escalation and impersonation; ML and consistency layers drive most false positives on benign orchestration traffic — see `benchmarks/results/report.md`.

## Getting started

```bash
py -3.12 -m pip install "inter-agent-guard[all,otel]"
# Download risk_scorer.onnx from GitHub Releases into agentguard/models/
py -3.12 -m agentguard status
```

```python
from agentguard import AgentGuard, CapabilityManifest

guard = AgentGuard(
    risk_threshold=0.75,
    task_objective="Analyse Q3 competitor pricing",
    require_ml_model=True,
)
guard.register_agent("researcher", CapabilityManifest.from_yaml("manifests/researcher.yaml"))
secured = guard.wrap(my_langgraph_graph)
```

## Dataset

Novel 6,200-example corpus (Anthropic Batch) is published on [Hugging Face](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1) for evaluation reproducibility. The library never calls Anthropic at runtime.

## Call to action

- PyPI: https://pypi.org/project/inter-agent-guard/
- GitHub: https://github.com/nizba06/agentguard
- Dataset: https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1
- Contributions welcome: adapters, rules, evasion reports

## References

- InjecAgent (Zhan et al., 2024)
- AgentDojo / Task Shield consistency checking
- Multi-agent injection literature (MASpi / ACIArena)
