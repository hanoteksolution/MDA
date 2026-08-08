from django.db import models

from core.models.base import BaseModel


class PlanModule(BaseModel):
    """Modules included in a SaaS subscription plan."""

    plan = models.ForeignKey(
        "platform.SubscriptionPlan",
        on_delete=models.CASCADE,
        related_name="plan_modules",
    )
    module = models.ForeignKey(
        "platform.Module",
        on_delete=models.CASCADE,
        related_name="plan_links",
    )
    included = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "plan_modules"
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "module"],
                name="uniq_plan_module",
            ),
        ]

    def __str__(self):
        state = "included" if self.included else "excluded"
        return f"{self.plan_id}:{self.module.code}={state}"
