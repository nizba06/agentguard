"""Shared firewall decision types and action/result constants."""

from __future__ import annotations

from dataclasses import dataclass

TRUST_PASS, TRUST_FAIL, TRUST_SKIP = "PASS", "FAIL", "SKIP"  # noqa: S105
CAP_PASS, CAP_FAIL, CAP_SKIP = "PASS", "FAIL", "SKIP"  # noqa: S105
ACTION_FORWARD, ACTION_QUARANTINE, ACTION_BLOCK = "FORWARD", "QUARANTINE", "BLOCK"

# Hard cap on inter-agent message size (1 MiB) to bound memory/CPU before tokenization.
MAX_MESSAGE_BYTES = 1_048_576

_MODEL_INSTALL_HINT = (
    "Install the ONNX model for enforce-mode ML scoring: "
    "python scripts/download_release_model.py "
    "(or copy artifacts via scripts/install_model.ps1 / install_model.sh). "
    "See README 'Production setup' and docs/source/latency.md for rules-only / monitor modes."
)


@dataclass(frozen=True)
class FirewallDecision:
    """Outcome of inspecting an inter-agent message."""

    action: str
    risk_score: float
    trust_result: str
    capability_result: str
    failure_reason: str | None
