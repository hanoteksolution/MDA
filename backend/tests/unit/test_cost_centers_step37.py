"""STEP 37 — Cost centers on journal lines."""

from decimal import Decimal

import pytest

from apps.finance.models import CostCenter, JournalEntry
from apps.finance.selectors.ledger import GeneralLedgerSelector
from apps.finance.services.chart_service import ChartService
from apps.finance.services.cost_center_service import CostCenterService
from apps.finance.services.journal_service import JournalService
from apps.finance.services.mapping_service import MappingService
from apps.platform.models import Tenant
from apps.settings_app.models import Branch, Company
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def cc_env(db):
    tenant = Tenant.objects.create(name="CC Co", slug="cc-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="CC Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    user = get_user_model().objects.create_user(
        username="cc_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    MappingService.seed_defaults(tenant_id=tenant.id)
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    rev = MappingService.resolve(key="DEFAULT_SALES_REVENUE", tenant_id=tenant.id)
    return {"tenant": tenant, "branch": branch, "user": user, "cash": cash, "rev": rev}


@pytest.mark.django_db
def test_seed_default_cost_centers(cc_env):
    # Chart ensure already seeds defaults; re-seed is idempotent.
    codes = set(
        CostCenter.active_objects()
        .filter(tenant_id=cc_env["tenant"].id)
        .values_list("code", flat=True)
    )
    assert {"HQ", "OPS", "SALES"} <= codes
    assert CostCenterService.seed_defaults(tenant_id=cc_env["tenant"].id) == []


@pytest.mark.django_db
def test_create_custom_cost_center(cc_env):
    cc = CostCenterService.create(
        data={"tenant_id": cc_env["tenant"].id, "code": "mkt", "name": "Marketing"},
        user=cc_env["user"],
    )
    assert cc.code == "MKT"
    assert cc.name == "Marketing"


@pytest.mark.django_db
def test_journal_line_with_cost_center(cc_env):
    CostCenterService.seed_defaults(tenant_id=cc_env["tenant"].id)
    ops = CostCenter.active_objects().get(tenant_id=cc_env["tenant"].id, code="OPS")
    entry = JournalService.create_entry(
        data={
            "tenant_id": cc_env["tenant"].id,
            "entry_date": timezone.localdate(),
            "description": "Ops cash sale",
            "status": JournalEntry.STATUS_POSTED,
            "lines": [
                {
                    "account_id": str(cc_env["cash"].id),
                    "debit": "80",
                    "credit": "0",
                    "cost_center_id": str(ops.id),
                },
                {
                    "account_id": str(cc_env["rev"].id),
                    "debit": "0",
                    "credit": "80",
                    "cost_center_code": "OPS",
                },
            ],
        },
        user=cc_env["user"],
    )
    data = JournalService.serialize(entry)
    assert all(line["cost_center_code"] == "OPS" for line in data["lines"])

    gl = GeneralLedgerSelector.run(
        account_id=cc_env["cash"].id,
        cost_center_id=ops.id,
        user=cc_env["user"],
    )
    assert gl["closing_balance"] == 80.0
    assert gl["cost_center_id"] == str(ops.id)
