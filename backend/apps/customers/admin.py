from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_code", "full_name", "phone", "customer_type", "is_active")
    search_fields = ("customer_code", "full_name", "email", "phone")
