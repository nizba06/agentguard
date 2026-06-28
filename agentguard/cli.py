"""AgentGuard command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

from agentguard import __version__
from agentguard.audit.logger import AppendOnlyLogger
from agentguard.capability.manifest import CapabilityManifest
from agentguard.firewall import AgentGuard
from agentguard.inspector.ml_scorer import ModelNotLoadedWarning
from agentguard.inspector.model_paths import default_model_path, missing_model_files


def _cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.logfile)
    if not path.exists():
        print(f"Error: log file not found: {path}", file=sys.stderr)
        return 1

    ok, err = AppendOnlyLogger().verify_chain(path)
    line_count = sum(1 for line in path.open(encoding="utf-8") if line.strip())

    if args.json:
        print(
            json.dumps(
                {
                    "valid": ok,
                    "error": err,
                    "path": str(path),
                    "entry_count": line_count,
                }
            )
        )
        return 0 if ok else 2

    if ok:
        print(f"OK: chain valid ({line_count} entries) - {path}")
        return 0

    print(f"FAIL: {err} - {path}", file=sys.stderr)
    return 2


def _cmd_version(_: argparse.Namespace) -> int:
    print(f"agentguard {__version__}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    model = default_model_path()
    loaded = model.exists()
    missing = missing_model_files() if not loaded else []
    payload = {
        "version": __version__,
        "model_path": str(model),
        "model_present": loaded,
        "missing_files": missing,
    }
    if args.json:
        print(json.dumps(payload))
    else:
        print(f"agentguard {__version__}")
        print(f"model_path: {model}")
        print(f"model_present: {loaded}")
        if missing:
            print(f"missing_files: {', '.join(missing)}")
            print("Install: see README Production setup or ./scripts/install_model.sh")
    return 0 if loaded else 1


def _cmd_check_manifest(args: argparse.Namespace) -> int:
    path = Path(args.manifest)
    if not path.exists():
        print(f"Error: manifest not found: {path}", file=sys.stderr)
        return 1
    try:
        manifest = CapabilityManifest.from_yaml(str(path))
    except Exception as exc:  # noqa: BLE001 — surface validation errors to CLI users
        if args.json:
            print(json.dumps({"valid": False, "path": str(path), "error": str(exc)}))
        else:
            print(f"FAIL: {path}: {exc}", file=sys.stderr)
        return 2

    summary = {
        "valid": True,
        "path": str(path),
        "agent_id": manifest.agent_id,
        "permitted_tools": manifest.permitted_tools,
        "forbidden_tools": manifest.forbidden_tools,
        "permitted_endpoints": manifest.permitted_endpoints,
        "external_contact": manifest.external_contact,
        "can_spawn_agents": manifest.can_spawn_agents,
        "max_delegation_depth": manifest.max_delegation_depth,
        "max_output_tokens": manifest.max_output_tokens,
    }
    if args.json:
        print(json.dumps(summary))
    else:
        print(f"OK: {manifest.agent_id} - {path}")
        print(f"  permitted_tools: {len(manifest.permitted_tools)}")
        print(f"  external_contact: {manifest.external_contact}")
        print(f"  permitted_endpoints: {len(manifest.permitted_endpoints)}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    import tempfile

    message = args.message
    if args.file:
        message = Path(args.file).read_text(encoding="utf-8")
    if message is None:
        print("Error: provide --message or --file", file=sys.stderr)
        return 1

    if args.audit_log:
        audit_path = str(args.audit_log)
        cleanup_audit = False
    else:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
            prefix="agentguard-inspect-",
            suffix=".jsonl",
            delete=False,
        )
        audit_path = tmp.name
        tmp.close()
        cleanup_audit = True

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ModelNotLoadedWarning)
            guard = AgentGuard(
                audit_log_path=audit_path,
                enable_trust_attestation=False,
                enable_capability_enforcement=False,
                enable_consistency_check=False,
                include_message_preview=False,
                mode="enforce",
            )

        payload = message.encode("utf-8")
        decision = guard.inspect_message("cli", "cli", message, payload, signature=None)
        result = {
            "action": decision.action,
            "risk_score": decision.risk_score,
            "trust_result": decision.trust_result,
            "capability_result": decision.capability_result,
            "failure_reason": decision.failure_reason,
            "ml_model_loaded": guard.is_ml_model_loaded,
        }
        if args.json:
            print(json.dumps(result))
        else:
            print(f"action: {decision.action}")
            print(f"risk_score: {decision.risk_score:.4f}")
            print(f"ml_model_loaded: {guard.is_ml_model_loaded}")
            if decision.failure_reason:
                print(f"failure_reason: {decision.failure_reason}")
        return 0 if decision.action == "FORWARD" else 2
    finally:
        if cleanup_audit:
            Path(audit_path).unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="agentguard",
        description="AgentGuard — inter-agent security middleware utilities",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser(
        "verify",
        help="Verify hash-chain integrity of an audit JSONL log",
    )
    verify.add_argument("logfile", help="Path to audit.jsonl")
    verify.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON result",
    )
    verify.set_defaults(func=_cmd_verify)

    version = sub.add_parser("version", help="Print package version")
    version.set_defaults(func=_cmd_version)

    status = sub.add_parser("status", help="Show install and ML model status")
    status.add_argument("--json", action="store_true", help="Emit JSON")
    status.set_defaults(func=_cmd_status)

    check = sub.add_parser("check-manifest", help="Validate a capability YAML manifest")
    check.add_argument("manifest", help="Path to capability manifest YAML")
    check.add_argument("--json", action="store_true", help="Emit JSON")
    check.set_defaults(func=_cmd_check_manifest)

    inspect = sub.add_parser(
        "inspect",
        help="Score a message with rule filter + ML scorer (no trust/capability)",
    )
    inspect.add_argument("--message", "-m", help="Message text to inspect")
    inspect.add_argument("--file", "-f", help="Read message text from a file")
    inspect.add_argument(
        "--audit-log",
        help="Optional audit log path (default: ./.agentguard-inspect-audit.jsonl)",
    )
    inspect.add_argument("--json", action="store_true", help="Emit JSON")
    inspect.set_defaults(func=_cmd_inspect)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
