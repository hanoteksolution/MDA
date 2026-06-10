from django.contrib import admin

from apps.sales.models import Invoice, Quotation


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("quotation_number", "customer", "status", "total_amount", "created_at")
    search_fields = ("quotation_number", "customer__full_name")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "status", "total_amount", "issue_date")
    search_fields = ("invoice_number", "customer__full_name")
