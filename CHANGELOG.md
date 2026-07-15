# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-07-15

### Added

- v1.0 ship gates: `scripts/check_v1_gates.py`, `scripts/ship_v1.ps1`
- Holdout evaluation path: `run_benchmark_evaluation.ps1 -Holdout`
- Dynamic INT8 ONNX release artifact (~164 MB)
- Documented CPU latency SLA exception (`docs/source/latency.md`)

### Changed

- Package version **1.0.0**
- Holdout metrics are the public authority (99.4% detection, 0.0% FPR on INT8)
- ONNX size NFR updated to &lt; 180 MB INT8
- `verify_model.py` hard-fails non-discriminative scorers; prefers holdout probes

## [Unreleased]

### Notes

- Post-1.0: GPU P95 measurements, consistency ablation write-up, optional smaller student model

## [0.1.1] - 2026-07-12

### Changed

- Split `firewall.py` into a thin public entry point (`AgentGuard`) plus
  `firewall_ops.FirewallEngine` / `firewall_types` (restores the 150-line
  `.cursorrules` cap on the entry module)
- Default `risk_threshold` raised from 0.75 → 0.85 and
  `consistency_ml_risk_floor` from 0.15 → 0.40 to reduce false positives
- Expanded rule filter to 50+ high-precision signatures; removed bare
  `"act as"` (too broad for benign prose)
- `docs/REQUIREMENTS.md` reconciled with shipped reality: in-process Trust
  Authority, Python 3.11/3.12 only, and measured NFR table vs v1.0 targets
- Benchmark report refreshed on Anthropic corpus: 37.1% detection, 28.9% FPR,
  ~1.59 s P95 (CPU)

### Added

- `MCPOutputInspector.wrap_tool_async` and `AgentGuard.wrap_mcp_tool_async`
  for async MCP tool callables

### Fixed

- Rules-only / unloaded-model path no longer calls `MLRiskScorer.score()`
  (eliminates per-message `ModelNotLoadedWarning` spam)

## [0.1.0] - 2026-07-11

### Added

- Three-layer Message Inspector: Aho-Corasick rules, DeBERTa ONNX ML scorer, sentence-transformer consistency check
- Trust Verifier with Ed25519 signing via PyNaCl
- Capability Enforcer with YAML manifests and monotonic delegation attenuation
- Full capability field enforcement: endpoints, data sources, output tokens, spawn/delegation depth
- Hash-chained append-only audit log and optional OpenTelemetry export
- LangGraph, CrewAI, and AutoGen adapters (optional extras)
- CLI: `verify`, `version`, `status`, `check-manifest`, `inspect`
- Benchmark evaluation harness and public-source dataset builder
- Docker runtime image, pre-commit hooks, and CI on Python 3.11/3.12
- `LICENSE` (Apache-2.0), `CONTRIBUTING.md`, `SECURITY.md`, and model verification scripts
- Cross-platform `scripts/install_model.sh` alongside PowerShell installers

### Fixed

- Schema drift: `permitted_endpoints` now validated and loadable (`comms_agent.yaml`)
- Consistency checker false positives on benign pipeline status messages (combined threshold + ML risk floor)
- Benchmark audit log reset per run and false-positive attribution by layer
- `verify_model.py` uses inter-agent framed benign samples and pipeline score checks
- Training dataset includes bare benign imperatives to reduce InjectAgent format skew
- ML scorer treats unloaded model as zero risk for consistency gating (CI-safe)
- Clearer trust failure reasons (missing vs invalid vs unregistered sender)
- Message size hard cap (`max_message_bytes`) and optional audit preview redaction

### Known Limitations

- CPU ML inference latency (~1060 ms P95) exceeds the 15 ms design target; use GPU or async paths for high-frequency pipelines
- ONNX model must be downloaded separately (Kaggle training output or local train/export); not bundled in the PyPI wheel
- Novel Anthropic Batch benchmark corpus deferred to v1.0 launch
- Trust keys are ephemeral in-process only (no HSM/KMS persistence yet)
- PyPI distribution name is `inter-agent-guard` (bare `agentguard` blocked by existing `agent-guard`); import remains `agentguard`
- Published to PyPI as `inter-agent-guard` 0.1.0
- ONNX model and GitHub Releases / Hugging Face dataset — see `scripts/LAUNCH_CHECKLIST.md`
