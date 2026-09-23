"""Create / rotate / read integration secrets. The plaintext exists only inside these calls."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_write import write_audit
from apps.integrations.crypto import decrypt_secret, encrypt_secret
from apps.integrations.models import IntegrationCredential

MODULE = "integrations"


class CredentialError(ValueError):
    pass


class CredentialService:
    @staticmethod
    def serialize(credential: IntegrationCredential) -> dict:
        """The only representation that ever leaves the backend: no secret, no ciphertext."""
        return {
            "id": str(credential.pk),
            "label": credential.label,
            "has_secret": credential.has_secret,
            "masked_tail": credential.masked_tail,
            "rotated_at": credential.rotated_at.isoformat() if credential.rotated_at else None,
        }

    @staticmethod
    def _apply(credential, secret: str):
        secret = (secret or "").strip()
        if not secret:
            raise CredentialError("A secret value is required.")
        credential.encrypted_secret = encrypt_secret(secret)
        # Show a tail only when the secret is long enough that 4 chars reveal little.
        credential.secret_tail = secret[-4:] if len(secret) >= 12 else ""
        credential.rotated_at = timezone.now()

    @staticmethod
    @transaction.atomic
    def create(*, tenant, label: str, secret: str, actor=None, request=None) -> IntegrationCredential:
        if not (label or "").strip():
            raise CredentialError("A label is required.")
        credential = IntegrationCredential(tenant=tenant, label=label.strip(), created_by=actor)
        CredentialService._apply(credential, secret)
        credential.save()
        write_audit(
            action="create", module=MODULE, entity=credential, user=actor, request=request,
            new_values={"label": credential.label, "has_secret": True},
        )
        return credential

    @staticmethod
    @transaction.atomic
    def rotate(*, credential: IntegrationCredential, secret: str, actor=None, request=None):
        CredentialService._apply(credential, secret)
        credential.updated_by = actor
        credential.save()
        write_audit(
            action="update", module=MODULE, entity=credential, user=actor, request=request,
            new_values={"label": credential.label, "event": "secret_rotated"},
        )
        return credential

    @staticmethod
    def reveal(credential: IntegrationCredential | None) -> str | None:
        """Plaintext for an outbound provider call. Internal use only — never serialise this."""
        if credential is None or not credential.has_secret:
            return None
        return decrypt_secret(credential.encrypted_secret)
