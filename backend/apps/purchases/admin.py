from django.contrib import admin

from apps.purchases.models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "branch", "status", "total_amount", "order_date")
    list_filter = ("status", "branch")
    search_fields = ("order_number", "supplier__company_name")
    inlines = [PurchaseOrderItemInline]
