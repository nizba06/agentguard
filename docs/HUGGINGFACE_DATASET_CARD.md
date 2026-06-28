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
size_categories:
  - 1K<n<10K
---

# AgentGuard Inter-Agent Benchmark (v0.1)

6,200 inter-agent messages for evaluating injection detection in multi-agent AI pipelines.

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
  "source": "inject_agent",
  "label": 1
}
```

**Benign:**
```json
{
  "message_text": "...",
  "label": 0,
  "category": "task_delegation",
  "source": "pipeline_template"
}
```

## Provenance (v0.1)

Built with `benchmarks/build_dataset_from_public.py`:

- Adversarial payloads from [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent) + synthetic fill
- Inter-agent framing via AgentGuard template library
- Benign messages from LangGraph/CrewAI-style pipeline templates
- **Cost: $0**

## v1.0 upgrade

Planned: novel corpus via Anthropic Batch API (see AgentGuard `scripts/LAUNCH_CHECKLIST.md`).

## Usage

```python
import json

with open("adversarial.jsonl") as f:
    for line in f:
        row = json.loads(line)
        print(row["attack_class"], row["message_text"][:80])
```

## Citation

```bibtex
@software{agentguard2026,
  title = {AgentGuard: Inter-Agent Security Middleware},
  year = {2026},
  url = {https://github.com/nizba06/agentguard}
}
```
