# Contributing to AgentGuard

Thanks for helping improve AgentGuard.

## Development setup

```bash
# Clone and install (Python 3.11 or 3.12)
poetry install --extras all --extras otel --with training

# Enable hooks
poetry run pre-commit install

# Run the suite
poetry run ruff check .
poetry run mypy agentguard
poetry run pytest
```

Optional ML model for enforce-mode and full benchmarks:

```bash
# Bash
./scripts/install_model.sh --help

# PowerShell
.\scripts\install_model.ps1 -SourceDir .\path\to\models
poetry run python scripts/verify_model.py
```

Check install health:

```bash
poetry run agentguard status
poetry run agentguard check-manifest manifests/comms_agent.yaml
```

## Coding standards

- Target Python 3.11+; keep `from __future__ import annotations`.
- Pass **ruff** (selected rules in `pyproject.toml`) and **mypy --strict**.
- Prefer small, focused modules; avoid drive-by refactors unrelated to the change.
- Do not commit secrets, `*.onnx` weights, local audit logs, or Kaggle scratch dirs.
- Capability schema changes must update `agentguard/schemas/capability_manifest.schema.json`, `CapabilityManifest`, enforcer checks, example manifests, and tests together.

## Tests

- Unit/integration tests live under `tests/`.
- Default tests disable auto-loading the ONNX model (`conftest.py`).
- Mark real-model tests with `@pytest.mark.ml_model`.
- Coverage gate is 85% (`pytest --cov-fail-under=85`).

## Pull requests

1. Keep PRs focused on one concern.
2. Include tests for new enforcement paths and CLI commands.
3. Update `CHANGELOG.md` under Unreleased when user-facing behavior changes.
4. Run `poetry run pytest` and lint before requesting review.

## Security

Report vulnerabilities via [SECURITY.md](SECURITY.md). Do not open public issues for exploitable flaws.
