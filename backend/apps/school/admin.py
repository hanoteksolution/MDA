"""Academic writes use domain services, including for platform staff."""
from django.contrib import admin
from apps.school.repositories.foundation import MODELS
from apps.school.models import SchoolProfile

class SchoolReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

for model in [SchoolProfile, *[m for m in MODELS.values() if m._meta.app_label == "school"]]:
    admin.site.register(model, SchoolReadOnlyAdmin)
