"""Append-only cryptographically chained JSONL audit logger."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditLogEntry:
    """Structured audit log entry returned from write_entry."""

    entry_id: str
    prev_hash: str
    message_hash: str
    sender_id: str
    recipient_id: str
    timestamp_ns: int
    risk_score: float | None
    trust_result: str
    capability_result: str
    action: str
    failure_reason: str | None
    message_preview: str | None


def _sha256_hex(data: str | bytes) -> str:
    """Return SHA-256 hex digest of data."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


class AppendOnlyLogger:
    """Append-only JSONL logger with hash-chained entries."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        """Initialise logger, optionally backing to a JSONL file.

        Args:
            log_path: Destination file path. When None, entries are kept in memory only.
        """
        self._log_path = Path(log_path) if log_path else None
        self._lock = threading.Lock()
        self._prev_hash = GENESIS_HASH
        self._entries: list[AuditLogEntry] = []
        if self._log_path and self._log_path.exists():
            self._resume_chain()

    def _resume_chain(self) -> None:
        """Resume chain state from an existing log file."""
        if self._log_path is None:
            return
        with self._log_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    self._prev_hash = _sha256_hex(line)

    def write_entry(
        self,
        *,
        sender_id: str,
        recipient_id: str,
        risk_score: float | None,
        trust_result: str,
        capability_result: str,
        action: str,
        failure_reason: str | None,
        message_preview: str | None,
        payload_bytes: bytes,
    ) -> AuditLogEntry:
        """Append a chained audit entry. Never stores raw payload bytes.

        Args:
            sender_id: Sending agent identifier.
            recipient_id: Receiving agent identifier.
            risk_score: Inspection risk score, if applicable.
            trust_result: Trust check outcome (PASS, FAIL, or SKIP).
            capability_result: Capability check outcome (PASS, FAIL, or SKIP).
            action: FORWARD, QUARANTINE, or BLOCK.
            failure_reason: Human-readable failure reason, if any.
            message_preview: Optional truncated preview (max 120 chars).
            payload_bytes: Raw payload used only to compute message_hash.

        Returns:
            The written audit log entry.
        """
        preview = None
        if message_preview is not None:
            preview = message_preview[:120]

        entry = AuditLogEntry(
            entry_id=str(uuid.uuid4()),
            prev_hash=self._prev_hash,
            message_hash=_sha256_hex(payload_bytes),
            sender_id=sender_id,
            recipient_id=recipient_id,
            timestamp_ns=time.time_ns(),
            risk_score=risk_score,
            trust_result=trust_result,
            capability_result=capability_result,
            action=action,
            failure_reason=failure_reason,
            message_preview=preview,
        )

        record_line = self._serialize(entry)
        with self._lock:
            self._prev_hash = _sha256_hex(record_line)
            self._entries.append(entry)
            if self._log_path is not None:
                self._log_path.parent.mkdir(parents=True, exist_ok=True)
                with self._log_path.open("a", encoding="utf-8") as handle:
                    handle.write(record_line + "\n")
        return entry

    def _serialize(self, entry: AuditLogEntry) -> str:
        """Serialize entry to canonical JSON for chaining."""
        body: dict[str, Any] = {
            "entry_id": entry.entry_id,
            "prev_hash": entry.prev_hash,
            "message_hash": entry.message_hash,
            "sender_id": entry.sender_id,
            "recipient_id": entry.recipient_id,
            "timestamp_ns": entry.timestamp_ns,
            "risk_score": entry.risk_score,
            "trust_result": entry.trust_result,
            "capability_result": entry.capability_result,
            "action": entry.action,
            "failure_reason": entry.failure_reason,
            "message_preview": entry.message_preview,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    @property
    def entries(self) -> list[AuditLogEntry]:
        """Return a copy of in-memory entries."""
        return list(self._entries)

    def verify_chain(self, log_path: Path | str | None = None) -> tuple[bool, str | None]:
        """Verify hash-chain integrity.

        Args:
            log_path: Optional path override. Defaults to the configured log file.

        Returns:
            Tuple of (valid, error_message).
        """
        path = Path(log_path) if log_path else self._log_path
        if path is not None and path.exists():
            return self._verify_file(path)
        return self._verify_memory()

    def _verify_memory(self) -> tuple[bool, str | None]:
        prev_hash = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev_hash:
                return False, f"Broken chain at entry {entry.entry_id}"
            prev_hash = _sha256_hex(self._serialize(entry))
        return True, None

    def _verify_file(self, path: Path) -> tuple[bool, str | None]:
        prev_hash = GENESIS_HASH
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("prev_hash") != prev_hash:
                    return False, f"Broken chain at line {line_no}"
                prev_hash = _sha256_hex(line)
        return True, None
