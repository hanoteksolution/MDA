"""Hotel folio settlement at check-out — room invoice + POS AR clear."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.hotel.models import Folio, FolioLine, Reservation
from apps.hotel.services import HotelError, HotelService
from apps.inventory.models import Warehouse
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch
from core.tenancy import tenant_context


@pytest.fixture
def hotel_settle_env(db):
    from django.contrib.auth import get_user_model

    from apps.authentication.bootstrap import bootstrap_roles_and_permissions
    from apps.authentication.models import Role

    PlatformService.ensure_default_business_types()
    PlatformService.ensure_default_plans()
    ensure_default_modules()
    BusinessPresetService.ensure_default_presets()
    bootstrap_roles_and_permissions()
    tenant, _report = DemoTenantService.create(
        data={
            "name": "Settle Folio Demo",
            "business_type_code": "hotel",
            "preset_code": "hotel",
            "duration_days": 14,
            "generate_data": True,
        }
    )
    branch = Branch.active_objects().filter(tenant=tenant).first()
    User = get_user_model()
    role = Role.objects.filter(slug="cashier").first() or Role.objects.first()
    user = User.objects.create_user(
        username="hotel_settle_cashier",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=role,
    )
    with tenant_context(tenant, enforce=True):
        if not Customer.active_objects().filter(
            tenant=tenant, full_name__iexact="Walk-in Customer"
        ).exists():
            Customer.objects.create(
                tenant=tenant,
                customer_code="WALK",
                full_name="Walk-in Customer",
                branch=branch,
            )
        warehouse = Warehouse.active_objects().filter(tenant=tenant).first()
        if warehouse is None:
            warehouse = Warehouse.objects.create(
                branch=branch,
                tenant=tenant,
                name="Main WH",
                code="WH1",
                is_default=True,
            )
        category = Category.objects.create(name="F&B", tenant=tenant)
        unit = Unit.objects.create(name="Piece", abbreviation="pc", tenant=tenant)
        product = Product.objects.create(
            tenant=tenant,
            sku="SETTLE-FN-B",
            name="Mini Bar Drink",
            category=category,
            unit=unit,
            cost_price=Decimal("2"),
            selling_price=Decimal("10"),
        )
        inv = InventoryService.ensure_inventory_record(
            product=product, warehouse=warehouse
        )
        inv.quantity = Decimal("50")
        inv.reserved_quantity = Decimal("0")
        inv.tenant_id = tenant.id
        inv.save(
            update_fields=["quantity", "reserved_quantity", "tenant_id", "updated_at"]
        )
    return {
        "tenant": tenant,
        "branch": branch,
        "user": user,
        "product": product,
    }


@pytest.mark.django_db
def test_checkout_requires_payment_when_balance_due(hotel_settle_env):
    tenant = hotel_settle_env["tenant"]
    with tenant_context(tenant, enforce=True):
        reservation = (
            Reservation.active_objects()
            .filter(tenant=tenant, status=Reservation.STATUS_CHECKED_IN)
            .first()
        )
        assert reservation is not None
        folio = Folio.active_objects().get(reservation=reservation)
        assert folio.outstanding > 0
        with pytest.raises(HotelError, match="payment_method"):
            HotelService.check_out(reservation=reservation)


@pytest.mark.django_db
def test_checkout_settles_room_and_pos_charges(hotel_settle_env):
    tenant = hotel_settle_env["tenant"]
    branch = hotel_settle_env["branch"]
    user = hotel_settle_env["user"]
    product = hotel_settle_env["product"]

    with tenant_context(tenant, enforce=True):
        reservation = (
            Reservation.active_objects()
            .filter(tenant=tenant, status=Reservation.STATUS_CHECKED_IN)
            .select_related("room", "guest")
            .first()
        )
        assert reservation is not None
        folio = Folio.active_objects().get(reservation=reservation)
        room_balance = folio.balance

        result = PosService.checkout(
            data={
                "branch_id": str(branch.id),
                "customer_id": "walkin",
                "waiter_name": "Front Desk",
                "payment_method": "charge_to_room",
                "hotel_folio_id": str(folio.id),
                "items": [
                    {
                        "product_id": str(product.id),
                        "quantity": "1",
                        "unit_price": "10.00",
                    }
                ],
                "idempotency_key": f"settle-pos-{folio.id}",
            },
            user=user,
        )
        pos_invoice_number = result["invoice"]["number"]
        assert result["invoice"]["status"] == Invoice.STATUS_SENT

        folio.refresh_from_db()
        assert folio.balance == room_balance + Decimal("10.00")
        assert FolioLine.active_objects().filter(
            folio=folio, line_type=FolioLine.TYPE_FNB
        ).exists()

        HotelService.check_out(
            reservation=reservation,
            data={"payment_method": "cash", "payment_reference": "CHK-1"},
            user=user,
        )
        reservation.refresh_from_db()
        folio.refresh_from_db()
        assert reservation.status == Reservation.STATUS_CHECKED_OUT
        assert folio.status == Folio.STATUS_CLOSED
        assert folio.amount_paid == folio.balance
        assert folio.payment_method == "cash"
        assert folio.settled_at is not None

        pos_inv = Invoice.active_objects().get(invoice_number=pos_invoice_number)
        assert pos_inv.status == Invoice.STATUS_PAID

        room_inv = (
            Invoice.active_objects()
            .filter(tenant=tenant, notes__icontains=reservation.reservation_number)
            .exclude(pk=pos_inv.pk)
            .first()
        )
        assert room_inv is not None
        assert room_inv.status == Invoice.STATUS_PAID
        assert Decimal(str(room_inv.total_amount)) == room_balance
