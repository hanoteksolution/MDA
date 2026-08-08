"""Vertical report packs — hotel, restaurant, property (PHASE 21–23)."""

import pytest

from apps.hotel.models import Reservation, Room
from apps.platform.models import Tenant
from apps.platform.services.module_service import ensure_default_modules, sync_tenant_modules
from apps.property_management.models import Building, PropertyAsset, PropertyUnit
from apps.reports.services.report_service import ReportService
from apps.restaurant.models import DiningTable, MenuCategory, MenuItem
from apps.settings_app.models import Branch, Company
from core.tenancy import tenant_context


@pytest.fixture
def vertical_report_env(db):
    ensure_default_modules()
    tenant = Tenant.objects.create(
        name="Vertical Report Co",
        slug="vert-report-co",
        status=Tenant.STATUS_ACTIVE,
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=[
            "hotel",
            "restaurant",
            "property_management",
            "housing_rental",
            "office_rental",
            "inventory",
            "sales",
            "pos",
        ],
    )
    company = Company.objects.create(name="Vertical Report Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="Main", code="MAIN", is_default=True
    )
    with tenant_context(tenant, enforce=True):
        from apps.hotel.models import Guest, RoomType

        rt = RoomType.objects.create(
            tenant=tenant,
            branch=branch,
            name="Standard",
            code="STD",
            base_rate=50,
        )
        Room.objects.create(
            tenant=tenant,
            branch=branch,
            room_type=rt,
            code="101",
            status=Room.STATUS_OCCUPIED,
        )
        Room.objects.create(
            tenant=tenant,
            branch=branch,
            room_type=rt,
            code="102",
            status=Room.STATUS_VACANT,
        )
        guest = Guest.objects.create(
            tenant=tenant, branch=branch, full_name="Report Guest"
        )
        Reservation.objects.create(
            tenant=tenant,
            branch=branch,
            guest=guest,
            room_type=rt,
            room=Room.active_objects().filter(code="101").first(),
            reservation_number="RES-RPT-1",
            status=Reservation.STATUS_CHECKED_IN,
            check_in_date="2026-08-01",
            check_out_date="2026-08-05",
            rate_amount=50,
        )

        DiningTable.objects.create(
            tenant=tenant, branch=branch, code="T1", label="Window", capacity=4
        )
        cat = MenuCategory.objects.create(
            tenant=tenant, branch=branch, name="Mains"
        )
        MenuItem.objects.create(
            tenant=tenant,
            branch=branch,
            category=cat,
            name="Steak",
            unit_price=25,
        )

        asset = PropertyAsset.objects.create(
            tenant=tenant, branch=branch, name="Tower A", code="TA"
        )
        building = Building.objects.create(
            tenant=tenant, branch=branch, property_asset=asset, name="Block 1", code="B1"
        )
        PropertyUnit.objects.create(
            tenant=tenant,
            branch=branch,
            building=building,
            code="A-101",
            kind=PropertyUnit.KIND_RESIDENTIAL,
            status=PropertyUnit.STATUS_VACANT,
            rent_amount=800,
        )
    return {"tenant": tenant, "branch": branch}


@pytest.mark.django_db
def test_catalog_includes_vertical_packs(vertical_report_env):
    with tenant_context(vertical_report_env["tenant"], enforce=True):
        packs = ReportService.catalog()
    ids = {p["id"] for p in packs}
    assert "hotel" in ids
    assert "restaurant" in ids
    assert "property" in ids
    hotel = next(p for p in packs if p["id"] == "hotel")
    assert "Open Folios" in hotel["reports"]


@pytest.mark.django_db
def test_hotel_room_occupancy_report(vertical_report_env):
    with tenant_context(vertical_report_env["tenant"], enforce=True):
        data = ReportService.run(category="hotel", report="Room Occupancy")
    assert len(data["rows"]) == 2
    codes = {r["room"] for r in data["rows"]}
    assert codes == {"101", "102"}


@pytest.mark.django_db
def test_hotel_in_house_guests(vertical_report_env):
    with tenant_context(vertical_report_env["tenant"], enforce=True):
        data = ReportService.run(category="hotel", report="In-House Guests")
    assert len(data["rows"]) == 1
    assert data["rows"][0]["guest"] == "Report Guest"


@pytest.mark.django_db
def test_restaurant_table_and_menu(vertical_report_env):
    with tenant_context(vertical_report_env["tenant"], enforce=True):
        tables = ReportService.run(category="restaurant", report="Table Status")
        menu = ReportService.run(category="restaurant", report="Menu Catalog")
    assert len(tables["rows"]) == 1
    assert tables["rows"][0]["table"] == "T1"
    assert len(menu["rows"]) == 1
    assert menu["rows"][0]["item"] == "Steak"
    assert menu["rows"][0]["price"] == 25.0


@pytest.mark.django_db
def test_property_unit_occupancy(vertical_report_env):
    with tenant_context(vertical_report_env["tenant"], enforce=True):
        data = ReportService.run(category="property", report="Unit Occupancy")
    assert len(data["rows"]) == 1
    assert data["rows"][0]["unit"] == "A-101"
    assert data["rows"][0]["kind"] == "residential"
