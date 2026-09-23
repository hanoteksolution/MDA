"""Migration plan §4.2 — standard stock locations for every warehouse.

Deterministic and 1:1 with warehouses, so the reverse can safely empty the table:
`stock_locations` is created in this wave, so every row in it was created here.
"""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_stock_locations


def forwards(apps, schema_editor):
    result = backfill_stock_locations(apps=apps, using=schema_editor.connection.alias)
    if result.unresolved:
        print(f"\n  location backfill: {result}")


def backwards(apps, schema_editor):
    StockLocation = apps.get_model("organization", "StockLocation")
    StockLocation.objects.using(schema_editor.connection.alias).all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0002_backfill_default_branch"),
        ("inventory", "0003_stock_transfers"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
