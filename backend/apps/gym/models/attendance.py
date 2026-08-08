from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Attendance(TenantScopedModel, BaseModel):
    """Gym visit check-in / check-out record."""

    SOURCE_MANUAL = "manual"
    SOURCE_QR = "qr"
    SOURCE_BARCODE = "barcode"
    SOURCE_MEMBERSHIP_NUMBER = "membership_number"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_QR, "QR"),
        (SOURCE_BARCODE, "Barcode"),
        (SOURCE_MEMBERSHIP_NUMBER, "Membership number"),
    ]

    member = models.ForeignKey(
        "gym.Member",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    subscription = models.ForeignKey(
        "gym.MembershipSubscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_attendance",
    )
    check_in_at = models.DateTimeField(db_index=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=30, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "gym_attendance"
        ordering = ["-check_in_at"]
        indexes = [
            models.Index(
                fields=["tenant", "member", "check_in_at"],
                name="idx_gym_att_tenant_member_in",
            ),
        ]

    def __str__(self):
        return f"{self.member_id}@{self.check_in_at}"
