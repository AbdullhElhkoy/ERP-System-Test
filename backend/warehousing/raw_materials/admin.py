from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin

from .models import (
    Material,
    Supplier,
    MaterialStorage,
    MaterialTest,
    MaterialSpecification,
    RawMaterialDelivery,
    InventoryTransaction,
    RawMaterialLot,
    RawMaterialSample,
    RawMaterialAnalysis,
)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "material_code",
        "material_name",
        "is_active",
    )

    search_fields = (
        "material_code",
        "material_name",
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "supplier_code",
        "supplier_name",
        "phone",
        "is_active",
    )

    search_fields = (
        "supplier_code",
        "supplier_name",
    )


@admin.register(MaterialStorage)
class MaterialStorageAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"

    list_display = (
        "storage_code",
        "storage_name",
        "plant",
        "material",
        "allow_estimated_issue",
        "is_active",
    )

    list_filter = (
        "plant",
        "material",
        "allow_estimated_issue",
        "is_active",
    )

    search_fields = (
        "storage_code",
        "storage_name",
        "material__material_name",
    )
    
@admin.register(MaterialTest)
class MaterialTestAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "test_code",
        "test_name",
        "unit",
    )

    list_filter = (
        "material",
    )

    search_fields = (
        "test_code",
        "test_name",
    )


@admin.register(MaterialSpecification)
class MaterialSpecificationAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "test",
        "specification_min",
        "specification_max",
        "is_active",
    )

    list_filter = (
        "material",
        "is_active",
    )


@admin.register(RawMaterialDelivery)
class RawMaterialDeliveryAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"

    list_display = (
        "plant",
        "material",
        "supplier",
        "vehicle_number",
        "weight_tons",
        "decision",
        "arrived_at",
    )

    list_filter = (
        "plant",
        "material",
        "supplier",
        "decision",
    )

    search_fields = (
        "vehicle_number",
    )

    ordering = (
        "-arrived_at",
    )


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"

    list_display = (
        "plant",
        "material",
        "movement_type",
        "quantity_tons",
        "accuracy_type",
        "transaction_date",
    )

    list_filter = (
        "plant",
        "material",
        "movement_type",
    )

    ordering = (
        "-transaction_date",
    )


@admin.register(RawMaterialLot)
class RawMaterialLotAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "delivery__plant"

    list_display = (
        "lot_number",
        "delivery",
        "received_quantity",
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(RawMaterialSample)
class RawMaterialSampleAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"

    list_display = (
        "plant",
        "material",
        "sample_stage",
        "delivery",
        "sample_number",
        "sampled_at",
        "sampled_by",
    )

    list_filter = (
        "plant",
        "material",
        "sample_stage",
    )

    ordering = (
        "-sampled_at",
    )


@admin.register(RawMaterialAnalysis)
class RawMaterialAnalysisAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "sample__plant"

    list_display = (
        "sample",
        "test",
        "result",
        "is_conforming",
    )

    list_filter = (
        "test",
        "is_conforming",
    )

    ordering = (
        "test",
    )