"""Seed system catalog attributes for pharmacy business type (non-destructive)."""

from django.db import migrations


def seed_system_attributes(apps, schema_editor):
    AttributeDefinition = apps.get_model("products", "AttributeDefinition")
    AttributeOption = apps.get_model("products", "AttributeOption")
    BusinessTypeAttribute = apps.get_model("products", "BusinessTypeAttribute")
    BusinessType = apps.get_model("platform", "BusinessType")

    strength, _ = AttributeDefinition.objects.get_or_create(
        code="strength",
        tenant=None,
        defaults={
            "name": "Strength",
            "description": "Medicine strength (e.g. 500mg)",
            "data_type": "text",
            "is_required": False,
            "is_searchable": True,
            "is_filterable": True,
            "is_pos_visible": True,
            "is_reportable": True,
            "sort_order": 10,
        },
    )
    form, _ = AttributeDefinition.objects.get_or_create(
        code="dosage_form",
        tenant=None,
        defaults={
            "name": "Dosage form",
            "description": "Tablet, syrup, capsule, …",
            "data_type": "select",
            "is_required": False,
            "is_searchable": True,
            "is_filterable": True,
            "is_pos_visible": True,
            "is_reportable": True,
            "sort_order": 20,
        },
    )
    for idx, (value, label) in enumerate(
        [
            ("tablet", "Tablet"),
            ("capsule", "Capsule"),
            ("syrup", "Syrup"),
            ("injection", "Injection"),
            ("cream", "Cream"),
            ("other", "Other"),
        ]
    ):
        AttributeOption.objects.get_or_create(
            definition=form,
            value=value,
            defaults={"label": label, "sort_order": idx * 10},
        )

    pharmacy = BusinessType.objects.filter(code="pharmacy").first()
    if pharmacy:
        for defn, order in ((strength, 10), (form, 20)):
            BusinessTypeAttribute.objects.get_or_create(
                business_type=pharmacy,
                definition=defn,
                defaults={"sort_order": order, "is_required": False},
            )


def unseed(apps, schema_editor):
    # Keep seeded rows — reverse is a no-op for safety.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_attribute_engine"),
        ("platform", "0010_module_system"),
    ]

    operations = [
        migrations.RunPython(seed_system_attributes, unseed),
    ]
