"""Migration plan §4.3 — derive branch access from the legacy ``User.branch``.

Users with no legacy branch get nothing: they keep working through the legacy
fallback in ``core.branching`` until an administrator grants access. A user whose
tenant disagrees with their branch's tenant is flagged REVIEW_REQUIRED, not guessed.

``SchoolCampusAccess`` is deliberately not read — copying it would silently grant
retail branch access to School staff.

Reverse removes only the rows this backfill created, identified by their note.
"""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_user_branch_access

BACKFILL_NOTE = "Backfilled from legacy User.branch"


def forwards(apps, schema_editor):
    result = backfill_user_branch_access(apps=apps, using=schema_editor.connection.alias)
    if result.review_required or result.skipped:
        print(f"\n  access backfill: {result}")
        for detail in result.details:
            print(f"    - {detail}")


def backwards(apps, schema_editor):
    UserBranchAccess = apps.get_model("organization", "UserBranchAccess")
    UserBranchAccess.objects.using(schema_editor.connection.alias).filter(
        notes=BACKFILL_NOTE
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0003_backfill_stock_locations"),
        ("authentication", "0009_user_permission_revoke"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
