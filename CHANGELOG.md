# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - Unreleased

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
- Not yet published to PyPI / GitHub Releases (see `scripts/LAUNCH_CHECKLIST.md`)
