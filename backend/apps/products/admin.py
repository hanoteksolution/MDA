from django.contrib import admin

from apps.products.models import (
    AttributeDefinition,
    AttributeOption,
    Brand,
    BusinessTypeAttribute,
    Category,
    CategoryAttribute,
    Product,
    ProductAttributeValue,
    Unit,
)

admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Unit)
admin.site.register(Product)
admin.site.register(AttributeDefinition)
admin.site.register(AttributeOption)
admin.site.register(BusinessTypeAttribute)
admin.site.register(CategoryAttribute)
admin.site.register(ProductAttributeValue)
