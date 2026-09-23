"""Migration plan §4.1 — one default branch per tenant.

Tenants with no Company are skipped and reported; a tenant that has Branch rows but
no Company is flagged REVIEW_REQUIRED and left untouched. No Company is ever created.

Reverse is a deliberate no-op: un-defaulting a branch, or deleting one that other
rows may already reference, is more destructive than leaving the flag in place. The
schema change this accompanies is itself reversible.
"""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_default_branches


def forwards(apps, schema_editor):
    result = backfill_default_branches(apps=apps, using=schema_editor.connection.alias)
    if result.review_required:
        print(f"\n  branch backfill: {result}")
        for detail in result.details:
            print(f"    - {detail}")


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0001_initial"),
        ("settings_app", "0005_branch_profile_fields"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
