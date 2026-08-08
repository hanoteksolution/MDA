"""Hotel charge-to-room — POS checkout posts F&B onto open folio."""

from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.hotel.models import Folio, FolioLine, Reservation
from apps.hotel.services import HotelService
from apps.inventory.services.inventory_service import InventoryService
from apps.platform.services.business_preset_service import BusinessPresetService
from apps.platform.services.demo_tenant_service import DemoTenantService
from apps.platform.services.module_service import ensure_default_modules
from apps.platform.services.platform_service import PlatformService
from apps.products.models import Category, Product, Unit
from apps.sales.models import Invoice
from apps.sales.services.pos_profile import get_pos_capabilities, resolve_pos_profile_code
from apps.sales.services.pos_service import PosService
from apps.settings_app.models import Branch
from apps.inventory.models import Warehouse
from core.tenancy import tenant_context


@pytest.mark.django_db
@pytest.mark.parametrize(
    "modules,expected",
    [
        (["hotel", "pos"], "HOTEL_SERVICE"),
        (["hotel", "restaurant", "pos"], "HOTEL_SERVICE"),
        (["restaurant", "pos"], "RESTAURANT"),
    ],
)
def test_hotel_pos_profile_inference(modules, expected):
    assert resolve_pos_profile_code(enabled_modules=modules) == expected
    caps = get_pos_capabilities(enabled_modules=modules)
    assert caps["code"] == expected
    if "hotel" in modules:
        assert caps["capabilities"]["charge_to_room"] is True


@pytest.fixture
def hotel_pos_env(db):
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
            "name": "Charge Room Demo",
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
        username="hotel_pos_cashier",
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
            sku="ROOM-FN-B",
            name="Room Service Meal",
            category=category,
            unit=unit,
            cost_price=Decimal("5"),
            selling_price=Decimal("25"),
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
def test_charge_to_room_posts_folio_line(hotel_pos_env):
    tenant = hotel_pos_env["tenant"]
    branch = hotel_pos_env["branch"]
    user = hotel_pos_env["user"]
    product = hotel_pos_env["product"]

    with tenant_context(tenant, enforce=True):
        reservation = (
            Reservation.active_objects()
            .filter(tenant=tenant, status=Reservation.STATUS_CHECKED_IN)
            .select_related("room", "guest")
            .first()
        )
        assert reservation is not None
        folio = Folio.active_objects().get(reservation=reservation)
        assert folio.status == Folio.STATUS_OPEN
        balance_before = folio.balance

        open_list = HotelService.list_open_folios(branch_id=branch.id, user=user)
        assert any(str(f.id) == str(folio.id) for f in open_list)

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
                        "unit_price": "25.00",
                    }
                ],
                "idempotency_key": f"charge-room-{folio.id}",
            },
            user=user,
        )

        assert result["invoice"]["status"] == Invoice.STATUS_SENT
        assert result["receipt"]["payment_method"] == "charge_to_room"
        assert result["hotel_folio"]["id"] == str(folio.id)

        folio.refresh_from_db()
        assert folio.balance == balance_before + Decimal("25.00")
        line = (
            FolioLine.active_objects()
            .filter(folio=folio, line_type=FolioLine.TYPE_FNB)
            .order_by("-created_at")
            .first()
        )
        assert line is not None
        assert line.amount == Decimal("25.00")
        assert "invoice:" in (line.notes or "")
