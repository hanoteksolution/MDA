"""Fernet encryption for tenant-entered integration secrets (decision D6).

``INTEGRATION_ENCRYPTION_KEY`` holds one Fernet key, or several comma-separated for
rotation: the **first** encrypts, every key can decrypt (``MultiFernet``). With no key the
module refuses to work — it never falls back to storing plaintext.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class SecretDecryptError(ValueError):
    """The stored secret cannot be decrypted with the configured key(s)."""


def _fernet() -> MultiFernet:
    raw = (getattr(settings, "INTEGRATION_ENCRYPTION_KEY", "") or "").strip()
    if not raw:
        raise ImproperlyConfigured(
            "INTEGRATION_ENCRYPTION_KEY is not set; integration credentials cannot be stored "
            "or used. Generate one with cryptography.fernet.Fernet.generate_key()."
        )
    try:
        return MultiFernet([Fernet(k.strip().encode()) for k in raw.split(",") if k.strip()])
    except (ValueError, TypeError) as exc:
        # Never echo the key material itself.
        raise ImproperlyConfigured("INTEGRATION_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretDecryptError("Stored secret cannot be decrypted with the current key.") from exc


def rotate_token(token: str) -> str:
    """Re-encrypt under the primary key (after a key rotation)."""
    try:
        return _fernet().rotate(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretDecryptError("Stored secret cannot be decrypted with the current key.") from exc
