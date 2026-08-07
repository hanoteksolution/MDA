from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0004_document_sequence"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("sent", "Sent"),
                    ("paid", "Paid"),
                    ("overdue", "Overdue"),
                    ("on_hold", "On hold"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="draft",
                max_length=50,
            ),
        ),
    ]
