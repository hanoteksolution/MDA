"""STEP 35 Phase K — bank / cash reconciliation."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.finance.models import Account, BankReconciliation, JournalLine
from apps.finance.services.chart_service import ChartService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.reconciliation_service import (
    ReconciliationError,
    ReconciliationService,
)
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.models import Tenant
from apps.products.models import Category, Product, Unit
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context
from django.utils import timezone


@pytest.fixture
def bank_env(db):
    tenant = Tenant.objects.create(name="Bank Co", slug="bank-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Bank Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    from apps.inventory.models import Warehouse

    warehouse = Warehouse.objects.create(
        branch=branch, tenant=tenant, name="WH", code="WH1", is_default=True
    )
    category = Category.objects.create(name="General", tenant=tenant)
    unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
    product = Product.objects.create(
        tenant=tenant,
        sku="B-1",
        name="Bank Item",
        category=category,
        unit=unit,
        cost_price=Decimal("4"),
        selling_price=Decimal("10"),
    )
    inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse)
    inv.quantity = Decimal("50")
    inv.tenant_id = tenant.id
    inv.save(update_fields=["quantity", "tenant_id", "updated_at"])
    Customer.objects.create(
        tenant=tenant, customer_code="WALK", full_name="Walk-in Customer", branch=branch
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="bank_user", password="pass12345", tenant=tenant, branch=branch
    )
    ChartService.ensure_default_chart(tenant_id=tenant.id)
    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "user": user,
    }


@pytest.mark.django_db
def test_coa_splits_cash_bank_mobile(bank_env):
    tenant = bank_env["tenant"]
    codes = set(
        Account.active_objects().filter(tenant_id=tenant.id).values_list("code", flat=True)
    )
    assert "1000" in codes
    assert "1010" in codes
    assert "1020" in codes
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    bank = MappingService.resolve(key="DEFAULT_BANK", tenant_id=tenant.id)
    mobile = MappingService.resolve(key="DEFAULT_MOBILE_MONEY", tenant_id=tenant.id)
    assert cash.code == "1000"
    assert bank.code == "1010"
    assert mobile.code == "1020"


@pytest.mark.django_db
def test_bank_reconciliation_match_and_complete(bank_env):
    user = bank_env["user"]
    product = bank_env["product"]
    tenant = bank_env["tenant"]

    PosService.checkout(
        data={
            "branch_id": str(bank_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "10"}
            ],
        },
        user=user,
    )

    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)
    book_bal = ReconciliationService.book_balance_as_of(
        account=cash, as_of=timezone.localdate()
    )
    # Sale 10 revenue + COGS doesn't hit cash beyond 10 debit
    assert book_bal == Decimal("10.00")

    with tenant_context(tenant, enforce=True):
        rec = ReconciliationService.create(
            account_id=cash.id,
            statement_date=timezone.localdate(),
            statement_balance="10.00",
            user=user,
        )
        assert rec.status == BankReconciliation.STATUS_IN_PROGRESS
        assert Decimal(str(rec.book_balance)) == Decimal("10.00")

        jl = (
            JournalLine.active_objects()
            .filter(account=cash, debit__gt=0)
            .select_related("entry")
            .first()
        )
        assert jl is not None

        line = ReconciliationService.add_statement_line(
            reconciliation_id=rec.id,
            line_date=timezone.localdate(),
            amount="10",
            description="POS deposit",
            reference="DEP-1",
            user=user,
        )
        ReconciliationService.match(
            reconciliation_id=rec.id,
            statement_line_id=line.id,
            journal_line_id=jl.id,
            user=user,
        )
        summary = ReconciliationService.compute_summary(rec)
        assert summary["is_balanced"] is True
        assert summary["difference"] == 0.0

        completed = ReconciliationService.complete(reconciliation_id=rec.id, user=user)
        assert completed.status == BankReconciliation.STATUS_COMPLETED


@pytest.mark.django_db
def test_auto_match_and_outstanding_check(bank_env):
    user = bank_env["user"]
    product = bank_env["product"]
    tenant = bank_env["tenant"]

    # Two cash sales
    for _ in range(2):
        PosService.checkout(
            data={
                "branch_id": str(bank_env["branch"].id),
                "customer_id": "walkin",
                "waiter_name": "Alex",
                "payment_method": "cash",
                "items": [
                    {"product_id": str(product.id), "quantity": "1", "unit_price": "10"}
                ],
            },
            user=user,
        )

    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)

    with tenant_context(tenant, enforce=True):
        # Statement only shows one of the two deposits → outstanding book deposit
        rec = ReconciliationService.create(
            account_id=cash.id,
            statement_date=timezone.localdate(),
            statement_balance="10.00",
            user=user,
        )
        ReconciliationService.add_statement_line(
            reconciliation_id=rec.id,
            line_date=timezone.localdate(),
            amount="10",
            description="Cleared deposit",
            user=user,
        )
        result = ReconciliationService.auto_match(reconciliation_id=rec.id, user=user)
        assert result["matched"] == 1

        summary = ReconciliationService.compute_summary(rec)
        assert summary["unmatched_statement_count"] == 0
        assert summary["unmatched_book_deposits"] == 10.0
        assert summary["adjusted_book_balance"] == 10.0
        assert summary["is_balanced"] is True

        ReconciliationService.complete(reconciliation_id=rec.id, user=user)


@pytest.mark.django_db
def test_complete_rejects_unbalanced(bank_env):
    user = bank_env["user"]
    product = bank_env["product"]
    tenant = bank_env["tenant"]

    PosService.checkout(
        data={
            "branch_id": str(bank_env["branch"].id),
            "customer_id": "walkin",
            "waiter_name": "Alex",
            "payment_method": "cash",
            "items": [
                {"product_id": str(product.id), "quantity": "1", "unit_price": "10"}
            ],
        },
        user=user,
    )
    cash = MappingService.resolve(key="DEFAULT_CASH", tenant_id=tenant.id)

    with tenant_context(tenant, enforce=True):
        rec = ReconciliationService.create(
            account_id=cash.id,
            statement_date=timezone.localdate(),
            statement_balance="99.00",
            user=user,
        )
        with pytest.raises(ReconciliationError, match="not balanced"):
            ReconciliationService.complete(reconciliation_id=rec.id, user=user)
