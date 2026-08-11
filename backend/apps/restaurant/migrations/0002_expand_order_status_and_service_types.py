from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("restaurant", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="restaurantorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("open", "Open"),
                    ("submitted", "Submitted"),
                    ("preparing", "Preparing"),
                    ("sent", "Sent to kitchen"),
                    ("ready", "Ready"),
                    ("served", "Served"),
                    ("completed", "Completed"),
                    ("paid", "Paid"),
                    ("cancelled", "Cancelled"),
                    ("refunded", "Refunded"),
                    ("voided", "Voided"),
                ],
                db_index=True,
                default="open",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="restaurantorder",
            name="service_type",
            field=models.CharField(
                choices=[
                    ("dine_in", "Dine in"),
                    ("takeaway", "Takeaway"),
                    ("delivery", "Delivery"),
                    ("quick_sale", "Quick sale"),
                ],
                default="dine_in",
                max_length=20,
            ),
        ),
    ]
