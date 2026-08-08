"""STEP 57 — Pharmacy prescriptions thin MVP (PHASE 16)."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.pharmacy.models import Prescription
from apps.pharmacy.services.batch_service import BatchService
from apps.pharmacy.services.prescription_service import (
    PrescriptionError,
    PrescriptionService,
)
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.settings_app.models import Branch, Company


@pytest.fixture
def rx_env(db):
    tenant = Tenant.objects.create(
        name="Rx Co", slug="rx-co", status=Tenant.STATUS_ACTIVE
    )
    company = Company.objects.create(name="Rx Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["pharmacy", "inventory", "pos", "sales"],
        validate_dependencies=False,
    )
    user = get_user_model().objects.create_user(
        username="rx_user",
        password="pass12345",
        tenant=tenant,
        branch=branch,
    )
    return {"tenant": tenant, "branch": branch, "user": user}


@pytest.mark.django_db
def test_create_list_dispense_prescription(rx_env):
    user = rx_env["user"]
    rx = PrescriptionService.create(
        data={
            "patient_name": "Amina Ali",
            "patient_phone": "0700",
            "prescribed_by": "Dr. Hassan",
            "prescribed_at": date.today().isoformat(),
            "drug_name": "Amoxicillin 500",
            "dosage": "1 cap",
            "frequency": "TID",
            "quantity": 21,
        },
        user=user,
    )
    assert rx.rx_number.startswith("RX-")
    assert rx.status == Prescription.STATUS_ACTIVE
    assert rx.lines.count() == 1
    assert rx.lines.first().drug_name == "Amoxicillin 500"

    listed = list(PrescriptionService.list(user=user, search="Amina"))
    assert len(listed) == 1
    assert listed[0].id == rx.id

    ser = PrescriptionService.serialize(rx)
    assert ser["line_count"] == 1
    assert ser["patient_name"] == "Amina Ali"

    dispensed = PrescriptionService.dispense(prescription_id=rx.id, user=user)
    assert dispensed.status == Prescription.STATUS_DISPENSED
    assert dispensed.dispensed_at is not None
    assert dispensed.dispensed_by_id == user.id

    # Idempotent
    again = PrescriptionService.dispense(prescription_id=rx.id, user=user)
    assert again.status == Prescription.STATUS_DISPENSED


@pytest.mark.django_db
def test_create_requires_patient_and_line(rx_env):
    user = rx_env["user"]
    with pytest.raises(PrescriptionError, match="patient_name"):
        PrescriptionService.create(data={"drug_name": "X"}, user=user)
    with pytest.raises(PrescriptionError, match="line"):
        PrescriptionService.create(data={"patient_name": "No Line"}, user=user)


@pytest.mark.django_db
def test_summary_includes_rx_counts(rx_env):
    user = rx_env["user"]
    PrescriptionService.create(
        data={"patient_name": "P1", "drug_name": "Drug A", "quantity": 1},
        user=user,
    )
    rx2 = PrescriptionService.create(
        data={"patient_name": "P2", "drug_name": "Drug B", "quantity": 2},
        user=user,
    )
    PrescriptionService.dispense(prescription_id=rx2.id, user=user)

    summary = BatchService.summary(user=user)
    assert summary["prescriptions_total"] == 2
    assert summary["prescriptions_active"] == 1
    assert summary["prescriptions_dispensed"] == 1
