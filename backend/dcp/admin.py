from django.contrib import admin
from plants.models import Plant
from .models import FinalProductSiloReading, FinalProductSampleLot, FinalProductPacking, FinalProductRepacking


class FinalProductSampleLotInline(admin.TabularInline):
    model = FinalProductSampleLot
    extra = 0


@admin.register(FinalProductSiloReading)
class FinalProductSiloReadingAdmin(admin.ModelAdmin):
    list_display = ["sample_code", "plant", "silo", "represented_weight_tons", "cumulative_weight_tons", "sampled_at"]
    list_filter = ["plant", "silo", "sampled_at"]
    search_fields = ["sample_code", "sequence_number"]
    readonly_fields = ["plant"]  # قفل خانة اختيار المصنع
    inlines = [FinalProductSampleLotInline]

    class Media:
        js = ("dcp/js/silo_reading_admin.js",)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        Plant = FinalProductSiloReading._meta.get_field("plant").related_model
        default_plant = Plant.objects.filter(plant_code="DCP").first()
        if default_plant:
            initial["plant"] = default_plant.plant_id
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # قفل خانة المصنع: خيار واحد بس (DCP) وممنوع التغيير
        if db_field.name == "plant":
            kwargs["queryset"] = Plant.objects.filter(plant_code="DCP")
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "plant":
            field.widget.attrs["disabled"] = "disabled"
        return field

    def save_model(self, request, obj, form, change):
        if not obj.plant_id:
            Plant = obj._meta.get_field("plant").related_model
            default_plant = Plant.objects.filter(plant_code="DCP").first()
            if default_plant:
                obj.plant = default_plant
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        instance = form.instance
        if not instance.lots.exists():
            last_lot = (
                FinalProductSampleLot.objects
                .filter(silo_reading__plant_id=instance.plant_id)
                .exclude(silo_reading=instance)
                .order_by("-lot_number")
                .first()
            )
            start_lot = (last_lot.lot_number + 1) if last_lot else 1
            weight = int(instance.represented_weight_tons)
            absent_value = FinalProductSampleLot._meta.get_field("color_status").choices[2][0]

            for i in range(weight):
                FinalProductSampleLot.objects.create(
                    silo_reading=instance,
                    lot_number=start_lot + i,
                    color_status=absent_value,
                    im_status=absent_value,
                    over_status=absent_value,
                )

        instance.rebuild_sample_code()