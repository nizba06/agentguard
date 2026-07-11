---
license: apache-2.0
task_categories:
  - text-classification
language:
  - en
tags:
  - security
  - prompt-injection
  - multi-agent
  - agentguard
  - inter-agent-guard
size_categories:
  - 1K<n<10K
---

# AgentGuard Inter-Agent Benchmark (v1.0)

6,200 novel inter-agent messages for evaluating injection detection in multi-agent AI pipelines.

**Library:** [`inter-agent-guard`](https://pypi.org/project/inter-agent-guard/) on PyPI (import as `agentguard`).  
**Code:** https://github.com/nizba06/agentguard  
**Hub:** https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1

## Files

| File | Examples | Description |
|------|----------|-------------|
| `adversarial.jsonl` | 1,200 | Injection payloads in inter-agent framing (6 attack classes) |
| `benign.jsonl` | 5,000 | Legitimate orchestrator/agent/tool messages |

## Attack classes (200 each)

- `INDIRECT_INJECTION`
- `PROPAGATION`
- `IMPERSONATION`
- `CAPABILITY_ESCALATION`
- `MCP_POISONING`
- `GOAL_HIJACK`

## Benign categories (1,000 each)

- `task_delegation`, `result_report`, `tool_call_request`, `status_update`, `clarification_request`

## Schema

**Adversarial:**
```json
{
  "message_text": "...",
  "attack_class": "INDIRECT_INJECTION",
  "target_agent": "researcher",
  "subtlety_level": 3,
  "expected_detection_layer": "rule_filter",
  "source": "anthropic_batch_v1",
  "label": 1
}
```

**Benign:**
```json
{
  "message_text": "...",
  "label": 0,
  "category": "task_delegation",
  "source": "anthropic_batch_v1"
}
```

## Provenance

Generated via Anthropic Messages Batch API (single batch job, 2026-07-05):

- Batch id: `msgbatch_01Mqsiry38ceBD8MLcxzL2pK`
- Models: Claude Haiku 4.5 (benign + simpler adversarial), Claude Sonnet 4.5 (high-subtlety adversarial)
- Source tag: `anthropic_batch_v1`
- Chunk sizes: 20 adversarial / 40 benign per request

A zero-cost public-source builder also exists in the AgentGuard repo (`benchmarks/build_dataset_from_public.py`) for local development without this corpus.

## Reported metrics (AgentGuard v0.1.0, CPU ONNX)

| Metric | Value |
|--------|-------|
| Overall detection rate | 40.2% |
| False positive rate | 42.2% |
| P95 inspection latency | ~805 ms |

See `benchmarks/results/report.md` in the GitHub repository.

## Usage

```python
from datasets import load_dataset

ds = load_dataset("Nizba/agentguard-benchmark-v1")
```

Or download the JSONL files and run:

```bash
py -3.12 benchmarks/evaluate.py --require-model
```

## Citation

```bibtex
@software{agentguard2026,
  title = {AgentGuard: Inter-Agent Security Middleware},
  year = {2026},
  url = {https://github.com/nizba06/agentguard},
  note = {PyPI: inter-agent-guard}
}
```
