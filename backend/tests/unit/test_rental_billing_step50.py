"""Housing / office lease charges → Invoice + CAE (PHASE 21 slice)."""

from decimal import Decimal

import pytest

from apps.finance.models import AccountingEvent
from apps.finance.services.chart_service import ChartService
from apps.housing_rental.models import Lease, LeaseCharge
from apps.housing_rental.services import HousingService
from apps.office_rental.models import OfficeLease, OfficeLeaseCharge
from apps.office_rental.services import OfficeService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.sales.models import Invoice
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def housing_billing_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, _report = DemoTenantService.create(
        data={
            "name": "Housing Billing Demo",
            "business_type_code": "property",
            "preset_code": "property_residential",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch}


@pytest.fixture
def office_billing_env(db):
    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    tenant, _report = DemoTenantService.create(
        data={
            "name": "Office Billing Demo",
            "business_type_code": "property",
            "preset_code": "property_commercial",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch}


@pytest.mark.django_db
def test_housing_invoice_then_collect(housing_billing_env):
    tenant = housing_billing_env["tenant"]
    with tenant_context(tenant, enforce=True):
        lease = Lease.active_objects().filter(
            tenant=tenant, status=Lease.STATUS_ACTIVE
        ).first()
        assert lease is not None
        charge = HousingService.post_rent_charge(lease=lease)
        assert charge.status == LeaseCharge.STATUS_PENDING

        HousingService.invoice_charge(charge=charge)
        charge.refresh_from_db()
        assert charge.status == LeaseCharge.STATUS_INVOICED
        assert charge.invoice_id is not None
        invoice = charge.invoice
        assert invoice.status == Invoice.STATUS_SENT
        assert Decimal(str(invoice.total_amount)) == Decimal(str(charge.amount))

        HousingService.collect_charge(charge=charge, payment_method="cash")
        charge.refresh_from_db()
        invoice.refresh_from_db()
        assert charge.status == LeaseCharge.STATUS_PAID
        assert invoice.status == Invoice.STATUS_PAID

        assert AccountingEvent.active_objects().filter(
            tenant_id=tenant.id, source_id=invoice.id
        ).exists() or AccountingEvent.objects.filter(
            tenant_id=tenant.id, source_reference=invoice.invoice_number
        ).exists()


@pytest.mark.django_db
def test_housing_collect_pending_creates_paid_invoice(housing_billing_env):
    tenant = housing_billing_env["tenant"]
    with tenant_context(tenant, enforce=True):
        lease = Lease.active_objects().filter(
            tenant=tenant, status=Lease.STATUS_ACTIVE
        ).first()
        charge = HousingService.post_rent_charge(lease=lease)
        HousingService.collect_charge(charge=charge, payment_method="mobile")
        charge.refresh_from_db()
        assert charge.status == LeaseCharge.STATUS_PAID
        assert charge.invoice.status == Invoice.STATUS_PAID


@pytest.mark.django_db
def test_office_invoice_on_account(office_billing_env):
    tenant = office_billing_env["tenant"]
    with tenant_context(tenant, enforce=True):
        lease = OfficeLease.active_objects().filter(
            tenant=tenant, status=OfficeLease.STATUS_ACTIVE
        ).first()
        assert lease is not None
        charge = OfficeService.post_rent_charge(lease=lease)
        assert isinstance(charge, OfficeLeaseCharge)
        OfficeService.invoice_charge(charge=charge)
        charge.refresh_from_db()
        assert charge.status == OfficeLeaseCharge.STATUS_INVOICED
        assert charge.invoice.status == Invoice.STATUS_SENT
