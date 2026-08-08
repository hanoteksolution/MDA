"""STEP 52 / PHASE 09 — BusinessUnit dimension on journal lines + P&L filter."""

from decimal import Decimal

import pytest

from apps.finance.models import BusinessUnit, JournalEntry
from apps.finance.selectors.ledger import GeneralLedgerSelector
from apps.finance.selectors.profit_loss import ProfitLossSelector
from apps.finance.services.business_unit_service import BusinessUnitService
from apps.finance.services.chart_service import ChartService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def bu_env(db):
    tenant = Tenant.objects.create(name="BU Co", slug="bu-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="BU Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="bu_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user, "cash": cash, "rev": rev}


@pytest.mark.django_db
def test_seed_default_business_units(bu_env):
    codes = set(
        BusinessUnit.active_objects()
        .filter(tenant_id=bu_env["tenant"].id)
        .values_list("code", flat=True)
    )
    assert {"RETAIL", "GYM", "HOTEL", "PROP", "CORP"} <= codes
    assert BusinessUnitService.seed_defaults(tenant_id=bu_env["tenant"].id) == []


@pytest.mark.django_db
def test_create_custom_business_unit(bu_env):
    bu = BusinessUnitService.create(
        data={
            "tenant_id": bu_env["tenant"].id,
            "code": "spa",
            "name": "Spa",
            "module_code": "hotel",
        },
        user=bu_env["user"],
    )
    assert bu.code == "SPA"
    assert bu.module_code == "hotel"


@pytest.mark.django_db
def test_journal_stamps_bu_from_source_module_and_pnl_filters(bu_env):
    BusinessUnitService.seed_defaults(tenant_id=bu_env["tenant"].id)
    hotel_bu = BusinessUnit.active_objects().get(
        tenant_id=bu_env["tenant"].id, code="HOTEL"
    )
    entry = JournalService.create_entry(
        data={
            "tenant_id": bu_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Hotel room sale",
            "source_module": "hotel",
            "status": JournalEntry.STATUS_POSTED,
            "lines": [
                {
                    "account_id": str(bu_env["cash"].id),
                    "debit": "120",
                    "credit": "0",
                },
                {
                    "account_id": str(bu_env["rev"].id),
                    "debit": "0",
                    "credit": "120",
                },
            ],
        },
        user=bu_env["user"],
    )
    data = JournalService.serialize(entry)
    assert all(line["business_unit_code"] == "HOTEL" for line in data["lines"])

    gl = GeneralLedgerSelector.run(
        account_id=bu_env["cash"].id,
        business_unit_id=hotel_bu.id,
        user=bu_env["user"],
    )
    assert gl["closing_balance"] == 120.0
    assert gl["business_unit_id"] == str(hotel_bu.id)

    gym_bu = BusinessUnit.active_objects().get(tenant_id=bu_env["tenant"].id, code="GYM")
    gl_gym = GeneralLedgerSelector.run(
        account_id=bu_env["cash"].id,
        business_unit_id=gym_bu.id,
        user=bu_env["user"],
    )
    assert gl_gym["closing_balance"] == 0.0

    pl_hotel = ProfitLossSelector.run(
        business_unit_id=hotel_bu.id, user=bu_env["user"]
    )
    assert pl_hotel["totals"]["revenue"] == pytest.approx(120.0)
    assert pl_hotel["business_unit_id"] == str(hotel_bu.id)

    pl_gym = ProfitLossSelector.run(business_unit_id=gym_bu.id, user=bu_env["user"])
    assert pl_gym["totals"]["revenue"] == pytest.approx(0.0)


@pytest.mark.django_db
def test_explicit_business_unit_on_line(bu_env):
    BusinessUnitService.seed_defaults(tenant_id=bu_env["tenant"].id)
    gym = BusinessUnit.active_objects().get(tenant_id=bu_env["tenant"].id, code="GYM")
    entry = JournalService.create_entry(
        data={
            "tenant_id": bu_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Gym cash sale",
            "source_module": "pos",
            "status": JournalEntry.STATUS_POSTED,
            "lines": [
                {
                    "account_id": str(bu_env["cash"].id),
                    "debit": Decimal("50"),
                    "credit": "0",
                    "business_unit_id": str(gym.id),
                },
                {
                    "account_id": str(bu_env["rev"].id),
                    "debit": "0",
                    "credit": "50",
                    "business_unit_code": "GYM",
                },
            ],
        },
        user=bu_env["user"],
    )
    data = JournalService.serialize(entry)
    assert all(line["business_unit_code"] == "GYM" for line in data["lines"])
