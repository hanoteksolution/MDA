"""Migration plan §4.6 — JournalLine.branch from its entry (never infers entry branch)."""

from django.db import migrations

from apps.organization.services.backfill_service import backfill_journal_line_branch


def forwards(apps, schema_editor):
    backfill_journal_line_branch(apps=apps, using=schema_editor.connection.alias)


def backwards(apps, schema_editor):
    apps.get_model("finance", "JournalLine").objects.using(schema_editor.connection.alias).update(
        branch=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0010_journalline_branch"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
