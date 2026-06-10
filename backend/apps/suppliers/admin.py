from django.contrib import admin

from apps.suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_code", "company_name", "contact_person", "phone", "is_active")
    search_fields = ("supplier_code", "company_name", "contact_person")
