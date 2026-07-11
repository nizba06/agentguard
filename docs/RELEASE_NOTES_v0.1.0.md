# inter-agent-guard v0.1.0 — Release Notes

**Released:** 2026-07-11  
**PyPI:** `inter-agent-guard` · **Import:** `agentguard`  
**Repo:** AgentGuard (https://github.com/nizba06/agentguard)

## Highlights

- Three-layer Message Inspector: Aho-Corasick rules + DeBERTa ONNX ML scorer + consistency check
- Ed25519 trust attestation and YAML capability manifests (tools, endpoints, data sources, tokens, delegation)
- MCP tool output inspection
- Append-only hash-chained audit log
- CLI: `version`, `status`, `check-manifest`, `inspect`, `verify`
- Optional OpenTelemetry export (`[otel]` extra)
- Framework adapters: LangGraph, CrewAI, AutoGen

## Install

```bash
# PyPI distribution name; Python import remains agentguard
pip install inter-agent-guard
# optional adapters / telemetry
pip install "inter-agent-guard[all,otel]"
```

```python
from agentguard import AgentGuard, CapabilityManifest
```

> PyPI rejects bare `agentguard` as too similar to existing `agent-guard`. Use `inter-agent-guard`.

### ML model (required for enforce-mode scoring)

The ONNX scorer is **not** bundled in the PyPI wheel. Download from this release:

| Artifact | SHA-256 |
|----------|---------|
| `risk_scorer.onnx` | `f8f907c836426821ba0efc462ce6976c7b59296a90b6f837f014335cc3c39b56` |
| `model.sha256` | contains the same hash |

Place files under the package `models/` directory (or pass `model_path=` to `AgentGuard`), then:

```bash
agentguard status
python -c "from agentguard import AgentGuard; AgentGuard(require_ml_model=True)"
```

From a source checkout:

```bash
./scripts/install_model.sh /path/to/downloaded/artifacts
# or: .\scripts\install_model.ps1 -SourceDir ...
```

## Benchmark dataset (Hugging Face)

Novel 6,200-example inter-agent corpus (Anthropic Batch, `anthropic_batch_v1`):

**https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1**

- 1,200 adversarial (6 attack classes) + 5,000 benign messages
- Batch id: `msgbatch_01Mqsiry38ceBD8MLcxzL2pK`

## Benchmark results (Anthropic v1.0 corpus)

| Metric | Value |
|--------|-------|
| Overall detection rate | 40.2% |
| False positive rate | 42.2% |
| P95 inspection latency | ~805 ms (CPU ONNX) |

Full report: `benchmarks/results/report.md`.

## Known limitations

- CPU P95 latency ~800 ms (design target was 15 ms); use GPU ONNX providers or async inspection for high-frequency traffic
- On the novel Anthropic benchmark corpus, overall detection is ~40% with ~42% false positives — capability/trust layers catch manifest-style attacks; ML/consistency tuning is ongoing
- Trust keys are ephemeral and in-process only (no HSM/KMS persistence in v0.1.0)
- ONNX model shipped as a release artifact, not in the wheel
- Benchmark corpus for reported metrics is evaluated offline; novel Anthropic dataset: [Nizba/agentguard-benchmark-v1](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1)

## Verify

```bash
agentguard version
agentguard status
agentguard check-manifest manifests/comms_agent.yaml
agentguard inspect -m "Summarise public pricing data from filings."
```
