from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class IntegrationCredential(TenantScopedModel, BaseModel):
    """A tenant's secret for an external provider, encrypted at rest (D6).

    ``encrypted_secret`` is Fernet ciphertext. The plaintext is never stored, logged,
    audited or returned; callers only ever see ``has_secret`` and ``masked_tail``.
    """

    label = models.CharField(max_length=120)
    encrypted_secret = models.TextField(blank=True)
    secret_tail = models.CharField(max_length=4, blank=True)
    rotated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "integration_credentials"
        ordering = ["label"]

    def __str__(self):
        return self.label

    @property
    def has_secret(self) -> bool:
        return bool(self.encrypted_secret)

    @property
    def masked_tail(self) -> str:
        return f"••••{self.secret_tail}" if self.secret_tail else ""
