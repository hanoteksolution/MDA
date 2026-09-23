"""Migration plan §4.5 — default terminal/register per branch with POS history.

Calls the shared backfill so a management-command re-run uses identical logic.
Reverse detaches sessions but leaves the terminal/register rows (they are real
configuration once created; removing them could orphan later data).
"""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_pos_terminals


def forwards(apps, schema_editor):
    result = backfill_pos_terminals(apps=apps, using=schema_editor.connection.alias)
    if result.review_required:
        print(f"\n  pos terminal backfill: {result}")


def backwards(apps, schema_editor):
    CashierSession = apps.get_model("sales", "CashierSession")
    CashierSession.objects.using(schema_editor.connection.alias).update(
        terminal=None, register=None, warehouse=None, location=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0009_cashier_session_terminal_register"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
