"""Failed login audit trail (STEP 30 lockout)."""

from django.db import models


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    succeeded = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "login_attempts"
        indexes = [
            models.Index(fields=["username", "created_at"], name="idx_login_attempt_user_at"),
        ]

    def __str__(self):
        status = "ok" if self.succeeded else "fail"
        return f"{self.username} ({status}) @ {self.created_at}"
