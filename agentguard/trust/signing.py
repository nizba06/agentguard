"""Ed25519 signing and verification via PyNaCl."""

from __future__ import annotations

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an ephemeral Ed25519 keypair.

    Returns:
        Tuple of (public_key_bytes, private_key_bytes).
    """
    signing_key = SigningKey.generate()
    public_key = bytes(signing_key.verify_key)
    private_key = bytes(signing_key)
    return public_key, private_key


def sign_message(message: bytes, private_key: bytes) -> bytes:
    """Sign a message with an Ed25519 private key.

    Args:
        message: Raw message bytes to sign.
        private_key: 32-byte Ed25519 seed / private key.

    Returns:
        64-byte Ed25519 signature.
    """
    signing_key = SigningKey(private_key)
    signed = signing_key.sign(message)
    return bytes(signed.signature)


def verify_signature(message: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify an Ed25519 signature.

    Args:
        message: Original message bytes.
        signature: 64-byte signature to verify.
        public_key: 32-byte Ed25519 public key.

    Returns:
        True if the signature is valid.
    """
    try:
        verify_key = VerifyKey(public_key)
        verify_key.verify(message, signature)
    except (BadSignatureError, ValueError):
        return False
    return True
