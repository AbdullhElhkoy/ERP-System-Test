from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models import RawMaterialDelivery, PreMillingSample, PostMillingSample


@admin.register(RawMaterialDelivery)
class RawMaterialDeliveryAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "material_type", "vehicle_number", "supplier_name", "weight_tons", "decision", "arrived_at")
    list_filter = ("plant", "material_type", "decision")
    ordering = ("-arrived_at",)


@admin.register(PreMillingSample)
class PreMillingSampleAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "sampled_at", "p2o5_percentage", "humidity_percentage", "impurities_percentage")
    list_filter = ("plant",)
    ordering = ("-sampled_at",)


@admin.register(PostMillingSample)
class PostMillingSampleAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "sampled_at", "p2o5_percentage", "sieve_over_5mm", "sieve_over_2mm", "sieve_over_1mm", "sieve_over_0_5mm", "sieve_under_0_5mm")
    list_filter = ("plant",)
    ordering = ("-sampled_at",)