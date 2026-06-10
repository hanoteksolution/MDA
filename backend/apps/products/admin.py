from django.contrib import admin

from apps.products.models import Brand, Category, Product, Unit

admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Unit)
admin.site.register(Product)
