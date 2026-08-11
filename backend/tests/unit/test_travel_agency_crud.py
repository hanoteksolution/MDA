import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models.audit_log import AuditLog
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService
from apps.settings_app.models import Branch, Company
from apps.finance.models import JournalEntry
from apps.finance.services.cutover_service import AccountingCutoverService
from core.tenancy import tenant_context


@pytest.fixture
def travel_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    tenant = Tenant.objects.create(name="Travel Co", slug="travel-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="Travel Co", tenant=tenant)
    branch = Branch.objects.create(company=company, tenant=tenant, name="HQ", code="HQ", is_default=True)
    sync_tenant_modules(tenant=tenant, enabled_codes=["travel_agency", "sales", "purchases"], validate_dependencies=False)
    user = get_user_model().objects.create_user(username="travel_admin", password="pass12345", tenant=tenant, branch=branch, role=Role.objects.get(slug="super_admin"))
    return {"branch": branch, "user": user}


def client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")
    return client


@pytest.mark.django_db
def test_travel_booking_vertical_crud(travel_env):
    client = client_for(travel_env["user"])
    branch_id = str(travel_env["branch"].id)
    destination = client.post("/api/v1/travel/destinations/", {"country": "Japan", "city": "Tokyo", "name": "Tokyo", "code": "TYO"}, format="json")
    assert destination.status_code == 201, destination.content
    package = client.post("/api/v1/travel/packages/", {"name": "Tokyo Explorer", "code": "TOK-7", "destination_id": destination.json()["data"]["id"], "duration_days": 7, "base_price": "1500"}, format="json")
    assert package.status_code == 201, package.content
    traveler = client.post("/api/v1/travel/travelers/", {"full_name": "Ava Traveler", "passport_number": "P123"}, format="json")
    assert traveler.status_code == 201, traveler.content
    booking = client.post("/api/v1/travel/bookings/", {"branch_id": branch_id, "package_id": package.json()["data"]["id"], "travel_date": "2026-09-01", "return_date": "2026-09-08", "total_amount": "1500"}, format="json")
    assert booking.status_code == 201, booking.content
    booking_id = booking.json()["data"]["id"]
    assert booking.json()["data"]["status"] == "draft"
    assert client.post(f"/api/v1/travel/bookings/{booking_id}/status/", {"status": "confirmed"}, format="json").status_code == 200
    flight = client.post("/api/v1/travel/flights/", {"booking_id": booking_id, "airline": "Example Air", "flight_number": "EA100", "origin": "JFK", "destination": "NRT", "depart_at": "2026-09-01T10:00:00Z", "arrive_at": "2026-09-02T14:00:00Z"}, format="json")
    assert flight.status_code == 201, flight.content
    hotel = client.post("/api/v1/travel/hotel-stays/", {"booking_id": booking_id, "hotel_name": "Tokyo Inn", "city": "Tokyo", "check_in": "2026-09-02", "check_out": "2026-09-08", "rate": "100", "total_amount": "600"}, format="json")
    assert hotel.status_code == 201, hotel.content
    visa = client.post("/api/v1/travel/visas/", {"booking_id": booking_id, "traveler_id": traveler.json()["data"]["id"], "visa_type": "tourist", "country": "Japan", "fee_amount": "45"}, format="json")
    assert visa.status_code == 201, visa.content
    commission = client.post("/api/v1/travel/commissions/", {"booking_id": booking_id, "agent_name": "Ava Agent", "rate_percent": "10"}, format="json")
    assert commission.status_code == 201, commission.content
    assert commission.json()["data"]["amount"] == 150.0
    assert client.post(f"/api/v1/travel/commissions/{commission.json()['data']['id']}/status/", {"status": "approved"}, format="json").status_code == 200
    detail = client.get(f"/api/v1/travel/bookings/{booking_id}/")
    assert detail.status_code == 200
    assert len(detail.json()["data"]["flights"]) == 1
    assert len(detail.json()["data"]["hotel_stays"]) == 1
    invalid = client.post(f"/api/v1/travel/bookings/{booking_id}/status/", {"status": "draft"}, format="json")
    assert invalid.status_code == 400
    assert AuditLog.objects.filter(module="travel_agency", action="create").exists()


@pytest.mark.django_db
def test_travel_insurance_transfer_itinerary_and_activity(travel_env):
    client = client_for(travel_env["user"])
    branch_id = str(travel_env["branch"].id)
    booking = client.post("/api/v1/travel/bookings/", {"branch_id": branch_id, "travel_date": "2026-09-01", "total_amount": "500"}, format="json")
    traveler = client.post("/api/v1/travel/travelers/", {"full_name": "Sam Traveler"}, format="json")
    booking_id, traveler_id = booking.json()["data"]["id"], traveler.json()["data"]["id"]
    insurance = client.post("/api/v1/travel/insurance/", {"booking_id": booking_id, "traveler_id": traveler_id, "provider": "SafeCo", "policy_number": "POL-1", "coverage_type": "medical", "start_date": "2026-09-01", "end_date": "2026-09-10", "premium_amount": "20"}, format="json")
    assert insurance.status_code == 201, insurance.content
    vehicle = client.post("/api/v1/travel/vehicles/", {"code": "VAN-1", "make_model": "Ford Transit", "plate_number": "ABC-1", "capacity": 12}, format="json")
    driver = client.post("/api/v1/travel/drivers/", {"full_name": "Driver One", "phone": "123", "license_number": "LIC-1"}, format="json")
    transfer = client.post("/api/v1/travel/transfers/", {"booking_id": booking_id, "vehicle_id": vehicle.json()["data"]["id"], "driver_id": driver.json()["data"]["id"], "pickup_location": "Airport", "dropoff_location": "Hotel", "pickup_at": "2026-09-01T10:00:00Z", "transfer_type": "airport", "amount": "40"}, format="json")
    assert transfer.status_code == 201, transfer.content
    itinerary = client.post("/api/v1/travel/itineraries/", {"booking_id": booking_id, "title": "Tokyo day one", "day_number": 1}, format="json")
    activity = client.post("/api/v1/travel/activities/", {"itinerary_id": itinerary.json()["data"]["id"], "name": "City tour", "cost": "30", "sort_order": 1}, format="json")
    assert activity.status_code == 201, activity.content


@pytest.mark.django_db
def test_accepted_quotation_converts_to_booking(travel_env):
    client = client_for(travel_env["user"])
    quote = client.post("/api/v1/travel/quotations/", {"branch_id": str(travel_env["branch"].id), "travel_date": "2026-10-01", "adults": 2, "subtotal": "1000", "tax_amount": "50", "total_amount": "1050", "valid_until": "2026-09-30"}, format="json")
    assert quote.status_code == 201, quote.content
    quote_id = quote.json()["data"]["id"]
    assert client.post(f"/api/v1/travel/quotations/{quote_id}/status/", {"status": "sent"}, format="json").status_code == 200
    assert client.post(f"/api/v1/travel/quotations/{quote_id}/status/", {"status": "accepted"}, format="json").status_code == 200
    booking = client.post(f"/api/v1/travel/quotations/{quote_id}/convert/", {}, format="json")
    assert booking.status_code == 200, booking.content
    assert booking.json()["data"]["total_amount"] == 1050.0


@pytest.mark.django_db
def test_confirmed_booking_posts_accounting_journal(travel_env):
    env = travel_env
    with tenant_context(env["branch"].tenant, enforce=True):
        AccountingCutoverService.prepare(tenant_id=env["branch"].tenant_id)
    client = client_for(env["user"])
    booking = client.post("/api/v1/travel/bookings/", {"branch_id": str(env["branch"].id), "travel_date": "2026-09-01", "total_amount": "750"}, format="json")
    booking_id = booking.json()["data"]["id"]
    posted = client.post(f"/api/v1/travel/bookings/{booking_id}/status/", {"status": "confirmed"}, format="json")
    assert posted.status_code == 200, posted.content
    ledger = client.post(f"/api/v1/travel/bookings/{booking_id}/post-accounting/", {}, format="json")
    assert ledger.status_code == 200, ledger.content
    assert ledger.json()["data"]["journal_entry_id"]
    assert JournalEntry.objects.filter(pk=ledger.json()["data"]["journal_entry_id"]).exists()


@pytest.mark.django_db
def test_travel_payment_and_refund_update_booking_and_post_accounting(travel_env):
    env = travel_env
    with tenant_context(env["branch"].tenant, enforce=True):
        AccountingCutoverService.prepare(tenant_id=env["branch"].tenant_id)
    client = client_for(env["user"])
    booking = client.post("/api/v1/travel/bookings/", {
        "branch_id": str(env["branch"].id), "travel_date": "2026-09-01", "total_amount": "750",
    }, format="json")
    booking_id = booking.json()["data"]["id"]
    assert client.post(f"/api/v1/travel/bookings/{booking_id}/status/", {"status": "confirmed"}, format="json").status_code == 200
    payment = client.post("/api/v1/travel/payments/", {
        "booking_id": booking_id, "amount": "300", "method": "card", "reference": "CARD-1",
    }, format="json")
    assert payment.status_code == 201, payment.content
    assert client.get(f"/api/v1/travel/bookings/{booking_id}/").json()["data"]["paid_amount"] == 300.0
    payment_post = client.post(f"/api/v1/travel/payments/{payment.json()['data']['id']}/post-accounting/", {}, format="json")
    assert payment_post.status_code == 200, payment_post.content
    assert payment_post.json()["data"]["journal_entry_id"]
    refund = client.post("/api/v1/travel/refunds/", {
        "booking_id": booking_id, "payment_id": payment.json()["data"]["id"], "amount": "125", "reason": "Customer cancellation",
    }, format="json")
    assert refund.status_code == 201, refund.content
    assert client.get(f"/api/v1/travel/bookings/{booking_id}/").json()["data"]["paid_amount"] == 175.0
    refund_post = client.post(f"/api/v1/travel/refunds/{refund.json()['data']['id']}/post-accounting/", {}, format="json")
    assert refund_post.status_code == 200, refund_post.content
    assert refund_post.json()["data"]["journal_entry_id"]
