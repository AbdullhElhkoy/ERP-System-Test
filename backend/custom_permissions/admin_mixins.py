from .models import get_viewable_plant_ids, get_editable_plant_ids


class PlantScopedAdminMixin:
    """
    Mixin عام لأي ModelAdmin مرتبط بمصنع.
    plant_lookup_field: المسار لحقل المصنع (مثلاً "plant" أو "silo__plant" للفلترة،
    وهيتقسم بـ "__" ويستخدم كمسار خصائص بايثون عادي للتحقق من صلاحية التعديل).
    """
    plant_lookup_field = "plant"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        viewable_ids = get_viewable_plant_ids(request.user)
        filter_kwargs = {f"{self.plant_lookup_field}__in": viewable_ids}
        return qs.filter(**filter_kwargs)

    def _get_object_plant_id(self, obj):
        value = obj
        for part in self.plant_lookup_field.split("__"):
            value = getattr(value, part)
        return value.plant_id if value else None

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_change_permission(request, obj)
        plant_id = self._get_object_plant_id(obj)
        return get_editable_plant_ids(request.user).filter(plant_id=plant_id).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)