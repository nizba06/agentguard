# AgentGuard v0.1.0 — Release Notes (Draft)

**Status:** Pre-release — pending full benchmark evaluation results.

## Highlights

- Inter-agent security middleware for LangGraph, CrewAI, and AutoGen
- Three-layer defence: rule filter + DeBERTa ML scorer + consistency check
- Ed25519 trust attestation and YAML capability manifests
- MCP tool output inspection (`MCPPoisoningException`)
- Append-only hash-chained audit log

## What's included

### Core (`agentguard/`)

- `firewall.py` — `AgentGuard`, `inspect_message()`, `wrap_mcp_tool()`
- `inspector/` — `InjectionRuleFilter`, `MLRiskScorer` (ONNX), `ConsistencyChecker`
- `trust/` — ephemeral keypairs, signing, verification
- `capability/` — manifest schema, enforcer, attenuation
- `mcp/` — `MCPOutputInspector`
- `adapters/` — LangGraph, CrewAI, AutoGen

### Training & models

- `training/` — dataset prep, DeBERTa fine-tuning, ONNX export, Kaggle notebook
- `agentguard/models/` — `risk_scorer.onnx` + SHA-256 + tokenizer (copy from Kaggle output)

### Benchmarks

- `benchmarks/build_dataset_from_public.py` — zero-cost 6,200-example dataset
- `benchmarks/evaluate.py` — evaluation harness + Markdown report
- `benchmarks/generate_dataset.py` — Anthropic Batch generator (v1.0 launch)

### Examples

- Vulnerable vs secured LangGraph pipeline
- MCP poisoning demo
- CrewAI and AutoGen adapter demos

## Benchmark results (pending)

Full evaluation running against 1,200 adversarial + 5,000 benign examples.

| Metric | Target | Result |
|--------|--------|--------|
| Detection rate | >90% combined | _TBD_ |
| False positive rate | <3% | _TBD_ |
| P95 latency (CPU) | <15 ms | _TBD_ |

See `benchmarks/results/report.md` when complete.

## Install

```bash
pip install agentguard
```

Or from source:

```bash
poetry install
poetry run pytest
```

## Breaking changes

N/A — initial release.

## Known limitations

- ML model must be trained separately on Kaggle GPU (~568 MB ONNX)
- Full CPU benchmark evaluation is slow (~6 s/example without batching)
- v0.1 dataset uses public-source derivation; v1.0 will add Anthropic-generated novel corpus

## Upgrade path to v1.0

See [scripts/LAUNCH_CHECKLIST.md](../scripts/LAUNCH_CHECKLIST.md).
