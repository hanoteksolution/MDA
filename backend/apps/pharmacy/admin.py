from django.contrib import admin

from apps.pharmacy.models import (
    BatchDispense,
    Prescription,
    PrescriptionLine,
    ProductBatch,
)

admin.site.register(ProductBatch)
admin.site.register(BatchDispense)
admin.site.register(Prescription)
admin.site.register(PrescriptionLine)
