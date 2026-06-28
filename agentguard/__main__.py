"""Allow ``python -m agentguard`` to invoke the CLI."""

from __future__ import annotations

from agentguard.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
