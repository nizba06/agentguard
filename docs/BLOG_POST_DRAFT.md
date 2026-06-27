# AgentGuard: Securing Multi-Agent AI Pipelines (Blog Draft)

> Fill benchmark numbers from `benchmarks/results/report.md` after evaluation completes.

## Title options

- AgentGuard: An Open-Source Firewall for Multi-Agent AI Systems
- Stopping Inter-Agent Injection Before It Propagates

## Hook (2–3 sentences)

Multi-agent systems trust messages between specialists — orchestrator, researcher, writer — without verifying content. One poisoned hop can hijack the entire pipeline. AgentGuard is a pip-installable Python middleware that inspects every inter-agent message at runtime.

## Problem

- Indirect injection in tool output and inter-agent messages
- Propagation across agent hops (LangGraph, CrewAI, AutoGen)
- No public benchmark for *inter-agent* injection specifically

## Solution overview

Three runtime layers:

1. **Message Inspector** — 40+ Aho-Corasick rules + DeBERTa ONNX scorer + consistency check
2. **Trust Verifier** — Ephemeral Ed25519 per-agent signing (PyNaCl)
3. **Capability Enforcer** — YAML manifests, monotonic attenuation

Plus **MCP output inspection** for tool-return poisoning (CVE-2025-32711 class).

## Demo: vulnerable vs secured pipeline

```bash
py -3.12 examples/vulnerable_pipeline/pipeline.py   # ATTACK SUCCEEDED
py -3.12 examples/secured_pipeline/pipeline.py      # ATTACK BLOCKED
```

## Benchmark results (TODO: paste from report.md)

| Metric | Value |
|--------|-------|
| Overall detection rate | _TBD_ |
| False positive rate | _TBD_ |
| P95 inspection latency | _TBD_ ms |
| Adversarial examples | 1,200 |
| Benign examples | 5,000 |
| ML model loaded | Yes |

### Detection by attack class

_Paste table from report.md § Detection Rate by Attack Class_

### Detection by layer

_Paste table from report.md § Detection by Layer_

## Architecture diagram

_Optional: LangGraph 3-agent pipeline with AgentGuard wrap point_

## Getting started

```bash
pip install agentguard  # v1.0
py -3.12 scripts/verify_model.py
```

```python
from agentguard import AgentGuard
guard = AgentGuard(risk_threshold=0.75)
secured = guard.wrap(my_langgraph_graph)
```

## Dataset

- **v0.1 (now):** Public-source benchmark — InjectAgent + inter-agent framing ([build script](../benchmarks/build_dataset_from_public.py))
- **v1.0 (launch):** Novel 6,200-example dataset via Anthropic Batch API

## Call to action

- GitHub: _repo URL_
- Hugging Face dataset: _URL_
- Contributions welcome: adapters, rules, evasion reports

## References

- InjecAgent (Zhan et al., 2024)
- MASpi / ACIArena multi-agent injection benchmarks
- Task Shield / AgentDojo consistency checking
