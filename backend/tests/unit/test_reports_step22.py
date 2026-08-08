"""STEP 22 — central reporting service, gym/pharmacy packs, catalog, export."""

import pytest

from apps.gym.models import Member, MembershipPlan, MembershipSubscription
from apps.gym.services.member_service import MemberService
from apps.gym.services.subscription_service import PlanService
from apps.pharmacy.models import ProductBatch
from apps.platform.models import Tenant
from apps.platform.services.module_service import ensure_default_modules, sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.reports.services.report_service import ReportService
from apps.inventory.models import Warehouse
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def report_env(db):
    ensure_default_modules()
    tenant = Tenant.objects.create(
        name="Report Co", slug="report-co", status=Tenant.STATUS_ACTIVE
    )
    sync_tenant_modules(tenant=tenant, enabled_codes=["gym", "pharmacy", "inventory", "sales"])
    company = Company.objects.create(name="Report Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    wh = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    member = MemberService.create(data={"full_name": "Rep Member", "tenant": tenant})
    plan = PlanService.create(
        data={"code": "basic", "name": "Basic", "duration_days": 30, "price": "40", "tenant": tenant}
    )
    sub = MembershipSubscription.objects.create(
        member=member,
        plan=plan,
        tenant_id=tenant.id,
        status=MembershipSubscription.STATUS_ACTIVE,
        price_paid=40,
    )
    cat = Category.objects.create(name="Meds", tenant=tenant)
    unit = Unit.objects.create(name="Box", abbreviation="bx", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="MED-1",
        name="Aspirin",
        category=cat,
        unit=unit,
        cost_price=1,
        selling_price=5,
    )
    ProductBatch.objects.create(
        tenant_id=tenant.id,
        product=product,
        warehouse=wh,
        batch_number="LOT-1",
        quantity=10,
        expiry_date="2026-12-31",
    )
    return {"tenant": tenant, "branch": branch, "member": member, "plan": plan}


@pytest.mark.django_db
def test_catalog_includes_gym_when_module_enabled(report_env):
    with tenant_context(report_env["tenant"], enforce=True):
        packs = ReportService.catalog()
    ids = {p["id"] for p in packs}
    assert "gym" in ids
    assert "pharmacy" in ids
    assert "sales" in ids


@pytest.mark.django_db
def test_gym_active_members_report(report_env):
    with tenant_context(report_env["tenant"], enforce=True):
        data = ReportService.run(category="gym", report="Active Members")
    assert data["columns"]
    assert len(data["rows"]) >= 1
    assert data["rows"][0]["member"] == "Rep Member"


@pytest.mark.django_db
def test_gym_subscription_summary_snapshot(report_env):
    with tenant_context(report_env["tenant"], enforce=True):
        data = ReportService.run(category="gym", report="Subscription Summary")
    assert data["rows"]
    row = data["rows"][0]
    assert row["plan"] == "Basic"
    assert row["status"] == "active"
    assert row["count"] == 1
    assert row["revenue"] == 40.0


@pytest.mark.django_db
def test_pharmacy_batch_stock_report(report_env):
    with tenant_context(report_env["tenant"], enforce=True):
        data = ReportService.run(category="pharmacy", report="Batch Stock")
    assert len(data["rows"]) == 1
    assert data["rows"][0]["batch"] == "LOT-1"
    assert data["rows"][0]["qty"] == 10.0


@pytest.mark.django_db
def test_export_csv_has_header_and_rows(report_env):
    with tenant_context(report_env["tenant"], enforce=True):
        csv_body = ReportService.export_csv(
            category="gym",
            report="Active Members",
        )
    lines = csv_body.strip().splitlines()
    assert lines[0].startswith("member,")
    assert len(lines) >= 2


@pytest.mark.django_db
def test_catalog_hides_gym_without_module(report_env):
    sync_tenant_modules(
        tenant=report_env["tenant"], enabled_codes=["sales"], disable_missing=True
    )
    with tenant_context(report_env["tenant"], enforce=True):
        ids = {p["id"] for p in ReportService.catalog()}
    assert "gym" not in ids
    assert "pharmacy" not in ids
    assert "sales" in ids
