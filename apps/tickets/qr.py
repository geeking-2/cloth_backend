"""HMAC-signed QR tokens for tickets.

Token payload is a UUID4 (32 hex chars). Signature is HMAC-SHA256 of the token
using `settings.SECRET_KEY`, hex-encoded and truncated to 32 chars. Scanner
must verify signature matches to prevent forgery.
"""
import hmac
import hashlib
from django.conf import settings


def _key() -> bytes:
    return settings.SECRET_KEY.encode('utf-8')


def sign(token: str) -> str:
    """Return a hex HMAC signature (32 chars) for `token`."""
    digest = hmac.new(_key(), token.encode('utf-8'), hashlib.sha256).hexdigest()
    return digest[:32]


def verify(token: str, signature: str) -> bool:
    """Constant-time compare to prevent timing attacks."""
    expected = sign(token)
    return hmac.compare_digest(expected, signature or '')


def encode_qr_payload(token: str, signature: str) -> str:
    """Format the payload that goes into the QR image.
    Format: `ART1:<token>:<sig>` — prefix allows version bumps later.
    """
    return f'ART1:{token}:{signature}'


def decode_qr_payload(payload: str):
    """Return (token, signature) or raise ValueError on malformed input."""
    parts = (payload or '').strip().split(':')
    if len(parts) != 3 or parts[0] != 'ART1':
        raise ValueError('Invalid QR payload')
    return parts[1], parts[2]
