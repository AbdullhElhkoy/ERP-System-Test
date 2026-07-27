from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models import (
    ProductionRun,
    Silo,
    ProductionBatch,
    BigBag,
    SackType,
    SackConversion,
    Customer,
    OrderBatch,
)


@admin.register(ProductionRun)
class ProductionRunAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "run_number", "started_at", "ended_at", "is_closed")
    list_filter = ("plant", "is_closed")


@admin.register(Silo)
class SiloAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "code")
    list_filter = ("plant",)


@admin.register(ProductionBatch)
class ProductionBatchAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "silo__plant"
    list_display = ("sequence_number", "silo", "production_run", "produced_at")
    list_filter = ("silo__plant",)
    ordering = ("sequence_number",)


@admin.register(BigBag)
class BigBagAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "production_batch__silo__plant"
    list_display = ("bag_number", "production_batch", "status", "packed_at")
    list_filter = ("status",)
    ordering = ("bag_number",)



@admin.register(SackType)
class SackTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "nominal_weight_kg")


@admin.register(SackConversion)
class SackConversionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "big_bag__production_batch__silo__plant"
    list_display = ("big_bag", "sack_type", "sack_count", "converted_at")

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "is_export")


@admin.register(OrderBatch)
class OrderBatchAdmin(admin.ModelAdmin):
    list_display = ("order_reference", "customer", "total_weight_kg", "dispatched_at")
    filter_horizontal = ("whole_big_bags", "sack_conversions")