"""Secured pipeline — identical graph wrapped with AgentGuard."""

from __future__ import annotations

from pathlib import Path

from agentguard import AgentGuard, AgentGuardException, CapabilityManifest
from examples.vulnerable_pipeline.pipeline import INJECTED_INSTRUCTION


def _manifest(name: str) -> CapabilityManifest:
    root = Path(__file__).resolve().parents[2]
    return CapabilityManifest.from_yaml(str(root / "manifests" / f"{name}.yaml"))


def run_secured_pipeline(task: str = "Analyse Q3 competitor pricing") -> str | None:
    """Run the pipeline with AgentGuard; return block reason if attack blocked."""
    import examples.vulnerable_pipeline.pipeline as vuln

    guard = AgentGuard(
        audit_log_path=str(Path(__file__).resolve().parents[2] / "audit.jsonl"),
        enable_trust_attestation=True,
        task_objective=(
            "Multi-agent pipeline: analyse Q3 competitor pricing, delegate sub-tasks, "
            "share status updates and tool outputs, and draft internal reports."
        ),
        consistency_threshold=0.10,
        consistency_ml_risk_floor=0.15,
        require_ml_model=True,
    )
    guard.register_agent("orchestrator", _manifest("orchestrator"))
    guard.register_agent("researcher", _manifest("researcher"))
    guard.register_agent("writer", _manifest("writer"))
    guard.rotate_keys()

    vuln._guard_for_signing = guard  # noqa: SLF001

    from examples.vulnerable_pipeline.pipeline import build_graph

    graph = build_graph()
    secured = guard.wrap(graph)

    try:
        result = secured.invoke({"task": task, "messages": [], "writer_action": ""})  # type: ignore[union-attr]
        if INJECTED_INSTRUCTION in result.get("writer_action", ""):
            return None
        return "writer did not execute injected instruction"
    except AgentGuardException as exc:
        return exc.failure_reason or str(exc)
    finally:
        vuln._guard_for_signing = None


def main() -> None:
    """Run demo and print block outcome."""
    reason = run_secured_pipeline()
    if reason:
        print(f"ATTACK BLOCKED by AgentGuard: {reason}")
    else:
        print("ATTACK SUCCEEDED: agent followed injected instruction")


if __name__ == "__main__":
    main()
