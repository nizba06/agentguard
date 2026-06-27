"""Tests for trust attestation."""

from __future__ import annotations

import pytest

from agentguard.trust.authority import TrustAuthority
from agentguard.trust.signing import generate_keypair, sign_message, verify_signature


def test_generate_keypair_unique() -> None:
    pub1, priv1 = generate_keypair()
    pub2, priv2 = generate_keypair()
    assert pub1 != pub2
    assert len(pub1) == 32
    assert len(priv1) == 32


def test_sign_and_verify_roundtrip() -> None:
    public_key, private_key = generate_keypair()
    message = b"inter-agent task delegation"
    signature = sign_message(message, private_key)
    assert verify_signature(message, signature, public_key)


def test_tampered_message_fails() -> None:
    public_key, private_key = generate_keypair()
    signature = sign_message(b"original", private_key)
    assert not verify_signature(b"tampered", signature, public_key)


def test_trust_authority_register_and_sign() -> None:
    authority = TrustAuthority()
    authority.register_agent("orchestrator")
    message = b"delegate to researcher"
    signature = authority.sign_for_agent("orchestrator", message)
    assert verify_signature(message, signature, authority.get_public_key("orchestrator"))


def test_rotate_all_keys_invalidates_old_signatures() -> None:
    authority = TrustAuthority()
    authority.register_agent("agent-a")
    old_public = authority.get_public_key("agent-a")
    message = b"test"
    signature = authority.sign_for_agent("agent-a", message)
    authority.rotate_all_keys()
    new_public = authority.get_public_key("agent-a")
    assert old_public != new_public
    assert not verify_signature(message, signature, new_public)


def test_duplicate_registration_raises() -> None:
    authority = TrustAuthority()
    authority.register_agent("a")
    with pytest.raises(ValueError):
        authority.register_agent("a")


def test_unknown_agent_raises() -> None:
    authority = TrustAuthority()
    with pytest.raises(KeyError):
        authority.get_public_key("missing")
