from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Destination(TenantScopedModel, BaseModel):
    country = models.CharField(max_length=120, db_index=True)
    city = models.CharField(max_length=120, db_index=True)
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_destinations"
        ordering = ["country", "city", "name"]
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uniq_travel_destination_code")]

    def __str__(self):
        return f"{self.name} ({self.code})"


class TravelPackage(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_ACTIVE, STATUS_ARCHIVED = "draft", "active", "archived"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_ACTIVE, "Active"), (STATUS_ARCHIVED, "Archived")]
    name = models.CharField(max_length=200, db_index=True)
    code = models.CharField(max_length=40, db_index=True)
    destination = models.ForeignKey(Destination, null=True, blank=True, on_delete=models.SET_NULL, related_name="packages")
    duration_days = models.PositiveSmallIntegerField(default=1)
    base_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    description = models.TextField(blank=True)
    includes = models.TextField(blank=True)
    excludes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_packages"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uniq_travel_package_code")]

    def __str__(self):
        return self.name


class Traveler(TenantScopedModel, BaseModel):
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="travelers")
    full_name = models.CharField(max_length=200, db_index=True)
    passport_number = models.CharField(max_length=80, blank=True, db_index=True)
    nationality = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_travelers"
        ordering = ["full_name"]
        indexes = [models.Index(fields=["tenant", "passport_number"], name="idx_traveler_tenant_passport")]

    def __str__(self):
        return self.full_name


class TravelBooking(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_COMPLETED = "draft", "confirmed", "cancelled", "completed"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_CONFIRMED, "Confirmed"), (STATUS_CANCELLED, "Cancelled"), (STATUS_COMPLETED, "Completed")]
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.CASCADE, related_name="travel_bookings")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_bookings")
    package = models.ForeignKey(TravelPackage, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    booking_code = models.CharField(max_length=40, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    travel_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    notes = models.TextField(blank=True)
    journal_entry = models.ForeignKey(
        "finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="travel_bookings",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "travel_bookings"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["tenant", "booking_code"], name="uniq_travel_booking_code")]

    def __str__(self):
        return self.booking_code


class TravelBookingTraveler(TenantScopedModel, BaseModel):
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="booking_travelers")
    traveler = models.ForeignKey(Traveler, on_delete=models.PROTECT, related_name="booking_links")

    class Meta:
        db_table = "travel_booking_travelers"
        constraints = [models.UniqueConstraint(fields=["booking", "traveler"], name="uniq_travel_booking_traveler")]


class TravelPayment(TenantScopedModel, BaseModel):
    STATUS_RECORDED, STATUS_VOID = "recorded", "void"
    STATUS_CHOICES = [(STATUS_RECORDED, "Recorded"), (STATUS_VOID, "Void")]
    METHOD_CASH, METHOD_CARD, METHOD_TRANSFER, METHOD_MOBILE_MONEY = "cash", "card", "transfer", "mobile_money"
    METHOD_CHOICES = [(METHOD_CASH, "Cash"), (METHOD_CARD, "Card"), (METHOD_TRANSFER, "Bank transfer"), (METHOD_MOBILE_MONEY, "Mobile money")]
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH)
    paid_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECORDED, db_index=True)
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_payments")
    posted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_payments"
        ordering = ["-paid_at", "-created_at"]


class TravelRefund(TenantScopedModel, BaseModel):
    STATUS_RECORDED, STATUS_VOID = "recorded", "void"
    STATUS_CHOICES = [(STATUS_RECORDED, "Recorded"), (STATUS_VOID, "Void")]
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="refunds")
    payment = models.ForeignKey(TravelPayment, null=True, blank=True, on_delete=models.SET_NULL, related_name="refunds")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=255)
    refunded_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECORDED, db_index=True)
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_refunds")
    posted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_refunds"
        ordering = ["-refunded_at", "-created_at"]


class TravelExpense(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_APPROVED, STATUS_PAID = "draft", "approved", "paid"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_APPROVED, "Approved"), (STATUS_PAID, "Paid")]
    branch = models.ForeignKey("settings_app.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_expenses")
    booking = models.ForeignKey(TravelBooking, null=True, blank=True, on_delete=models.SET_NULL, related_name="expenses")
    category = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expense_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_expenses"
        ordering = ["-expense_date", "-created_at"]


class FlightSegment(TenantScopedModel, BaseModel):
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="flights")
    airline = models.CharField(max_length=120)
    flight_number = models.CharField(max_length=30)
    origin = models.CharField(max_length=80)
    destination = models.CharField(max_length=80)
    depart_at = models.DateTimeField()
    arrive_at = models.DateTimeField()
    cabin_class = models.CharField(max_length=40, blank=True)
    pnr = models.CharField(max_length=40, blank=True)
    fare_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default="scheduled", db_index=True)

    class Meta:
        db_table = "travel_flight_segments"


class HotelStay(TenantScopedModel, BaseModel):
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="hotel_stays")
    hotel_name = models.CharField(max_length=180)
    city = models.CharField(max_length=120)
    check_in = models.DateField()
    check_out = models.DateField()
    room_type = models.CharField(max_length=120, blank=True)
    nights = models.PositiveSmallIntegerField(default=1)
    rate = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    confirmation_number = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=30, default="confirmed", db_index=True)

    class Meta:
        db_table = "travel_hotel_stays"


class VisaApplication(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_SUBMITTED, STATUS_APPROVED, STATUS_REJECTED = "draft", "submitted", "approved", "rejected"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_SUBMITTED, "Submitted"), (STATUS_APPROVED, "Approved"), (STATUS_REJECTED, "Rejected")]
    booking = models.ForeignKey(TravelBooking, null=True, blank=True, on_delete=models.SET_NULL, related_name="visa_applications")
    traveler = models.ForeignKey(Traveler, on_delete=models.PROTECT, related_name="visa_applications")
    visa_type = models.CharField(max_length=80)
    country = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_visa_applications"


class TravelCommission(TenantScopedModel, BaseModel):
    STATUS_PENDING, STATUS_APPROVED, STATUS_PAID = "pending", "approved", "paid"
    STATUS_CHOICES = [(STATUS_PENDING, "Pending"), (STATUS_APPROVED, "Approved"), (STATUS_PAID, "Paid")]
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="commissions")
    agent_name = models.CharField(max_length=160)
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_commissions"


class TravelInsurance(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_ACTIVE, STATUS_EXPIRED, STATUS_CANCELLED = "draft", "active", "expired", "cancelled"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_ACTIVE, "Active"), (STATUS_EXPIRED, "Expired"), (STATUS_CANCELLED, "Cancelled")]
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="insurance_policies")
    traveler = models.ForeignKey(Traveler, null=True, blank=True, on_delete=models.SET_NULL, related_name="insurance_policies")
    provider = models.CharField(max_length=160)
    policy_number = models.CharField(max_length=100)
    coverage_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    premium_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_insurance"
        constraints = [models.UniqueConstraint(fields=["tenant", "policy_number"], name="uniq_travel_insurance_policy")]


class TravelVehicle(TenantScopedModel, BaseModel):
    STATUS_AVAILABLE, STATUS_ASSIGNED, STATUS_MAINTENANCE = "available", "assigned", "maintenance"
    STATUS_CHOICES = [(STATUS_AVAILABLE, "Available"), (STATUS_ASSIGNED, "Assigned"), (STATUS_MAINTENANCE, "Maintenance")]
    code = models.CharField(max_length=40, db_index=True)
    make_model = models.CharField(max_length=160)
    plate_number = models.CharField(max_length=60)
    capacity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)

    class Meta:
        db_table = "travel_vehicles"
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uniq_travel_vehicle_code")]

    def __str__(self):
        return f"{self.code} — {self.make_model}"


class TravelDriver(TenantScopedModel, BaseModel):
    STATUS_ACTIVE, STATUS_INACTIVE = "active", "inactive"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Active"), (STATUS_INACTIVE, "Inactive")]
    full_name = models.CharField(max_length=200, db_index=True)
    phone = models.CharField(max_length=40)
    license_number = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    class Meta:
        db_table = "travel_drivers"
        constraints = [models.UniqueConstraint(fields=["tenant", "license_number"], name="uniq_travel_driver_license")]

    def __str__(self):
        return self.full_name


class TravelTransfer(TenantScopedModel, BaseModel):
    STATUS_SCHEDULED, STATUS_COMPLETED, STATUS_CANCELLED = "scheduled", "completed", "cancelled"
    TYPE_AIRPORT, TYPE_HOTEL, TYPE_TOUR, TYPE_OTHER = "airport", "hotel", "tour", "other"
    STATUS_CHOICES = [(STATUS_SCHEDULED, "Scheduled"), (STATUS_COMPLETED, "Completed"), (STATUS_CANCELLED, "Cancelled")]
    TYPE_CHOICES = [(TYPE_AIRPORT, "Airport"), (TYPE_HOTEL, "Hotel"), (TYPE_TOUR, "Tour"), (TYPE_OTHER, "Other")]
    booking = models.ForeignKey(TravelBooking, on_delete=models.CASCADE, related_name="transfers")
    vehicle = models.ForeignKey(TravelVehicle, null=True, blank=True, on_delete=models.SET_NULL, related_name="transfers")
    driver = models.ForeignKey(TravelDriver, null=True, blank=True, on_delete=models.SET_NULL, related_name="transfers")
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_at = models.DateTimeField()
    transfer_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True)

    class Meta:
        db_table = "travel_transfers"


class TravelItinerary(TenantScopedModel, BaseModel):
    package = models.ForeignKey(TravelPackage, null=True, blank=True, on_delete=models.SET_NULL, related_name="itineraries")
    booking = models.ForeignKey(TravelBooking, null=True, blank=True, on_delete=models.SET_NULL, related_name="itineraries")
    title = models.CharField(max_length=200)
    day_number = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=30, default="planned", db_index=True)

    class Meta:
        db_table = "travel_itineraries"
        ordering = ["day_number", "created_at"]


class TravelActivity(TenantScopedModel, BaseModel):
    itinerary = models.ForeignKey(TravelItinerary, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "travel_activities"
        ordering = ["sort_order", "created_at"]


class TravelQuotation(TenantScopedModel, BaseModel):
    STATUS_DRAFT, STATUS_SENT, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_EXPIRED = "draft", "sent", "accepted", "rejected", "expired"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_SENT, "Sent"), (STATUS_ACCEPTED, "Accepted"), (STATUS_REJECTED, "Rejected"), (STATUS_EXPIRED, "Expired")]
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.CASCADE, related_name="travel_quotations")
    quote_number = models.CharField(max_length=40, db_index=True)
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="travel_quotations")
    package = models.ForeignKey(TravelPackage, null=True, blank=True, on_delete=models.SET_NULL, related_name="quotations")
    travel_date = models.DateField(null=True, blank=True)
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_quotations"
        constraints = [models.UniqueConstraint(fields=["tenant", "quote_number"], name="uniq_travel_quote_number")]

    def __str__(self):
        return self.quote_number


class TravelQuotationLine(TenantScopedModel, BaseModel):
    quotation = models.ForeignKey(TravelQuotation, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "travel_quotation_lines"


class TravelDocument(TenantScopedModel, BaseModel):
    TYPE_PASSPORT, TYPE_VISA, TYPE_ID, TYPE_OTHER = "passport", "visa", "id", "other"
    TYPE_CHOICES = [(TYPE_PASSPORT, "Passport"), (TYPE_VISA, "Visa"), (TYPE_ID, "ID"), (TYPE_OTHER, "Other")]
    traveler = models.ForeignKey(Traveler, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    doc_number = models.CharField(max_length=120)
    issued_country = models.CharField(max_length=120, blank=True)
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "travel_documents"
