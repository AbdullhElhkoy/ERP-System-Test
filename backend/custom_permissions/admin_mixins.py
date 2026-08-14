from .models import get_viewable_plant_ids, get_editable_plant_ids


class PlantScopedAdminMixin:
    """
    Mixin عام لأي ModelAdmin مرتبط بمصنع.
    plant_lookup_field: المسار لحقل المصنع (مثلاً "plant" أو "silo__plant" للفلترة،
    وهيتقسم بـ "__" ويستخدم كمسار خصائص بايثون عادي للتحقق من صلاحية التعديل).
    """
    plant_lookup_field = "plant"

    def _context_plant_id(self, request):
        """المصنع الحالي: من رابط الفلترة أو من جلسة السياق."""
        raw = request.GET.get(f"{self.plant_lookup_field}__id__exact") or request.GET.get("plant__id__exact")
        if raw:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
        return request.session.get("factory_current_plant_id")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        plant_id = self._context_plant_id(request)
        if plant_id:
            return qs.filter(**{f"{self.plant_lookup_field}__id": plant_id})
        if request.user.is_superuser:
            return qs
        viewable_ids = get_viewable_plant_ids(request.user)
        filter_kwargs = {f"{self.plant_lookup_field}__in": viewable_ids}
        return qs.filter(**filter_kwargs)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        plant_id = self._context_plant_id(request)
        if plant_id and self.plant_lookup_field == "plant" and "plant" in form.base_fields:
            from plants.models import Plant
            field = form.base_fields["plant"]
            field.queryset = Plant.objects.filter(pk=plant_id)
            field.initial = plant_id
        return form

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if initial is None:
            initial = {}
        plant_id = self._context_plant_id(request)
        if plant_id and self.plant_lookup_field == "plant" and "plant" not in initial:
            initial["plant"] = plant_id
        return initial

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