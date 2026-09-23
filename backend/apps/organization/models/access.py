"""Branch membership and per-branch permission profiles.

`settings_app.Branch` stays the canonical ERP branch (decision D1); nothing here
duplicates it. These models answer two questions the rest of the ERP needs:

* which branches may this user act in?
* which of that user's permissions apply *in that branch*?

A profile can only ever **narrow** a user's global permissions, never widen them,
so branch access can never become a privilege-escalation path.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class BranchAccessProfile(TenantScopedModel, BaseModel):
    """A named bundle of permission codenames applied to a user within one branch."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        "authentication.Permission",
        blank=True,
        related_name="branch_access_profiles",
        db_table="branch_access_profile_permissions",
    )
    grants_all_permissions = models.BooleanField(
        default=False,
        help_text=(
            "No narrowing: the holder's full global permission set applies in the branch. "
            "Explicit, so that a profile with an empty permission list means 'nothing' "
            "rather than accidentally meaning 'everything'."
        ),
    )
    is_manager = models.BooleanField(
        default=False,
        help_text="Marks the holder as a manager of the branch (reporting/approval semantics).",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Seeded profile; kept in sync by bootstrap and not user-deletable.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "branch_access_profiles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(tenant__isnull=False, deleted_at__isnull=True),
                name="branch_access_profile_tenant_code_unique",
            )
        ]

    def __str__(self):
        return self.name

    def permission_codenames(self) -> set[str]:
        return set(
            self.permissions.filter(deleted_at__isnull=True).values_list("codename", flat=True)
        )


class UserBranchAccess(TenantScopedModel, BaseModel):
    """Grants one user the right to act in one branch, optionally narrowed by a profile."""

    STATUS_ACTIVE = "ACTIVE"
    STATUS_SUSPENDED = "SUSPENDED"
    STATUS_ENDED = "ENDED"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_ENDED, "Ended"),
    ]

    user = models.ForeignKey(
        "authentication.User", on_delete=models.CASCADE, related_name="branch_access"
    )
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="user_access"
    )
    access_profile = models.ForeignKey(
        BranchAccessProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_access",
        help_text="When empty the user's full global permission set applies in this branch.",
    )
    is_default = models.BooleanField(
        default=False, help_text="Branch selected on login when no branch is requested."
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "user_branch_access"
        ordering = ["branch__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "branch"],
                condition=models.Q(deleted_at__isnull=True),
                name="user_branch_access_unique",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "user", "status"]),
            models.Index(fields=["tenant", "branch", "status"]),
        ]

    def __str__(self):
        return f"{self.user_id} @ {self.branch_id}"

    def is_effective(self, *, on_date=None) -> bool:
        """Active status and inside the date window (both bounds optional)."""
        if self.deleted_at is not None or self.status != self.STATUS_ACTIVE:
            return False
        on_date = on_date or timezone.localdate()
        if self.starts_on and on_date < self.starts_on:
            return False
        if self.ends_on and on_date > self.ends_on:
            return False
        return True

    @classmethod
    def effective_filter(cls, *, on_date=None) -> models.Q:
        """Queryset form of :meth:`is_effective`, for use in a single query."""
        on_date = on_date or timezone.localdate()
        return (
            models.Q(deleted_at__isnull=True)
            & models.Q(status=cls.STATUS_ACTIVE)
            & (models.Q(starts_on__isnull=True) | models.Q(starts_on__lte=on_date))
            & (models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=on_date))
        )
