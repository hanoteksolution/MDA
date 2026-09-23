"""Migration plan §4.4 — StockMovement.branch / InventoryTransaction.branch backfill.

A pure FK dereference through Warehouse.branch (already NOT NULL), so every historical
row resolves deterministically; nothing is guessed. Reverse sets both columns back to
NULL, matching the migration plan's documented reverse.
"""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_ledger_branch


def forwards(apps, schema_editor):
    result = backfill_ledger_branch(apps=apps, using=schema_editor.connection.alias)
    if result.unresolved:
        print(f"\n  ledger branch backfill: {result}")


def backwards(apps, schema_editor):
    StockMovement = apps.get_model("inventory", "StockMovement")
    InventoryTransaction = apps.get_model("inventory", "InventoryTransaction")
    alias = schema_editor.connection.alias
    StockMovement.objects.using(alias).update(branch=None)
    InventoryTransaction.objects.using(alias).update(branch=None)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_stockmovement_branch_location"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
