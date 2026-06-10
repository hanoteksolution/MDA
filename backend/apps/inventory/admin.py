from django.contrib import admin

from apps.inventory.models import (
    Inventory,
    InventoryAdjustment,
    InventoryAdjustmentItem,
    InventoryTransaction,
    StockMovement,
    Warehouse,
)

admin.site.register(Warehouse)
admin.site.register(Inventory)
admin.site.register(StockMovement)
admin.site.register(InventoryTransaction)
admin.site.register(InventoryAdjustment)
admin.site.register(InventoryAdjustmentItem)
