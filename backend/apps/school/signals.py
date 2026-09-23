"""Clear live school leadership/teaching references on user deactivation.

Audit snapshots retain the old identity; no academic record is deleted.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.authentication.models import User
from apps.audit.services import write_audit
from apps.school.models import SchoolProfile, SchoolClass, Section, SubjectOffering
from apps.school.serializers.foundation import serialize


@receiver(post_save, sender=User, dispatch_uid="school_staff_deactivated")
def clear_inactive_staff(sender, instance, **kwargs):
    if instance.is_active and not instance.deleted_at:
        return
    with transaction.atomic():
        for model, field in ((SchoolProfile, "principal_user"), (SchoolClass, "teacher"), (Section, "teacher"), (SubjectOffering, "teacher")):
            for row in model.objects.filter(**{field:instance}):
                before = serialize(row)
                setattr(row, field, None)
                if isinstance(row, SchoolProfile):
                    row.principal_name = ""
                row.save()
                write_audit(action="staff_reference_cleared", module="school", entity=row, old_values=before, new_values=serialize(row))
