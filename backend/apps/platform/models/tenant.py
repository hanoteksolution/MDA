from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import BaseModel


class Tenant(BaseModel):
    """A shop / organization on the platform (maps to one or more companies)."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True, db_index=True)
    sync_secret = models.CharField(max_length=64, blank=True, db_index=True)
    shop_group = models.ForeignKey(
        "platform.ShopGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenants",
    )

    class Meta:
        db_table = "tenants"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubscriptionPlan(BaseModel):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=10)
    max_branches = models.PositiveIntegerField(default=3)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_plans"
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name


class TenantSubscription(BaseModel):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    reference_code = models.CharField(max_length=20, unique=True, db_index=True)
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="subscription",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL, db_index=True)
    started_at = models.DateField(default=timezone.localdate)
    expires_at = models.DateField(null=True, blank=True)
    last_paid_at = models.DateField(null=True, blank=True)
    billing_period_days = models.PositiveIntegerField(default=30)
    warning_days = models.PositiveIntegerField(default=5)
    grace_period_days = models.PositiveIntegerField(default=5)
    monthly_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    contact_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_subscriptions",
    )
    alert_title = models.CharField(max_length=200, blank=True)
    alert_message_template = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "tenant_subscriptions"

    def __str__(self):
        shop = self.tenant.name if self.tenant_id else "Unassigned"
        return f"{self.reference_code} — {shop} — {self.plan.name} ({self.status})"

    @property
    def days_until_expiry(self) -> int | None:
        if not self.expires_at:
            return None
        return (self.expires_at - timezone.localdate()).days

    @property
    def is_payment_current(self) -> bool:
        if not self.expires_at or not self.last_paid_at:
            return False
        period_start = self.expires_at - timedelta(days=self.billing_period_days)
        return self.last_paid_at >= period_start

    @property
    def is_usable(self) -> bool:
        if self.status == self.STATUS_SUSPENDED:
            return False
        today = timezone.localdate()
        if self.expires_at:
            grace_end = self.expires_at + timedelta(days=self.grace_period_days)
            if today > grace_end:
                return False
        return self.status in {
            self.STATUS_TRIAL,
            self.STATUS_ACTIVE,
            self.STATUS_EXPIRED,
        }

    @property
    def needs_payment_alert(self) -> bool:
        if self.status == self.STATUS_SUSPENDED or not self.expires_at:
            return False
        if self.is_payment_current:
            return False
        today = timezone.localdate()
        days_left = (self.expires_at - today).days
        if 0 <= days_left <= self.warning_days:
            return True
        if days_left < 0:
            grace_used = (today - self.expires_at).days
            return grace_used <= self.grace_period_days
        return False

    @property
    def effective_monthly_fee(self):
        if self.monthly_fee is not None:
            return self.monthly_fee
        return self.plan.monthly_price

    def alert_context(self) -> dict:
        today = timezone.localdate()
        days_left = self.days_until_expiry
        grace_remaining = None
        if self.expires_at and days_left is not None and days_left < 0:
            grace_remaining = max(self.grace_period_days - (today - self.expires_at).days, 0)
        contact_name = ""
        if self.contact_user_id:
            contact_name = self.contact_user.get_full_name() or self.contact_user.username
        return {
            "shop_name": self.tenant.name if self.tenant_id else "",
            "plan": self.plan.name,
            "reference": self.reference_code,
            "reference_code": self.reference_code,
            "monthly_fee": f"{self.effective_monthly_fee:.2f}",
            "days_left": days_left if days_left is not None else "",
            "grace_days": grace_remaining if grace_remaining is not None else "",
            "expires_at": self.expires_at.isoformat() if self.expires_at else "",
            "last_paid_at": self.last_paid_at.isoformat() if self.last_paid_at else "Never",
            "contact_user": contact_name,
            "status": self.status,
        }

    def _render_template(self, template: str) -> str:
        if not template.strip():
            return ""
        try:
            return template.format(**self.alert_context())
        except (KeyError, ValueError):
            return template

    def default_alert_title(self) -> str:
        days_left = self.days_until_expiry
        if days_left is not None and days_left < 0:
            return "Subscription Expired — Payment Overdue"
        return "Subscription Payment Required"

    def default_alert_message(self) -> str:
        ctx = self.alert_context()
        days_left = self.days_until_expiry
        if days_left is not None and days_left >= 0:
            return (
                f"Subscription payment is due for {ctx['shop_name']}. "
                f"{days_left} day(s) remaining before expiry on {ctx['expires_at']}. "
                f"Monthly fee: ${ctx['monthly_fee']}."
            )
        grace = ctx["grace_days"]
        return (
            f"Subscription for {ctx['shop_name']} has expired. "
            f"{grace} extension day(s) left before suspension. "
            f"Monthly fee: ${ctx['monthly_fee']}."
        )

    def alert_payload(self) -> dict:
        today = timezone.localdate()
        days_left = self.days_until_expiry
        if days_left is not None and days_left >= 0:
            severity = "warning"
        else:
            severity = "critical"
        title = self.alert_title.strip() or self.default_alert_title()
        custom = self._render_template(self.alert_message_template)
        message = custom or self.default_alert_message()
        ctx = self.alert_context()
        return {
            "subscription_id": str(self.id),
            "reference_code": self.reference_code,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "tenant_name": self.tenant.name if self.tenant_id else None,
            "contact_user_id": str(self.contact_user_id) if self.contact_user_id else None,
            "contact_user_name": ctx["contact_user"] or None,
            "plan": self.plan.name,
            "plan_code": self.plan.code,
            "status": self.status,
            "monthly_fee": float(self.effective_monthly_fee),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_paid_at": self.last_paid_at.isoformat() if self.last_paid_at else None,
            "days_until_expiry": days_left,
            "warning_days": self.warning_days,
            "grace_period_days": self.grace_period_days,
            "grace_days_remaining": max(
                self.grace_period_days - (today - self.expires_at).days, 0
            )
            if self.expires_at and days_left is not None and days_left < 0
            else None,
            "is_payment_current": self.is_payment_current,
            "severity": severity,
            "title": title,
            "message": message,
            "alert_title": self.alert_title,
            "alert_message_template": self.alert_message_template,
        }
