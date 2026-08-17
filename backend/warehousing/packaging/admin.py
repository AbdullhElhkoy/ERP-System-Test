from django.contrib import admin
from .models import (
    PackagingMaterial, PackagingSupplier, PackagingReceiving,
    PackagingStockLedger, PackagingStockBalance, FactoryPackagingStock,
    PackingOperation, PackagingReconciliation, SupplierEvaluation,
)


@admin.register(PackagingMaterial)
class PackagingMaterialAdmin(admin.ModelAdmin):
    list_display = ("material_code", "material_name", "category", "unit", "minimum_stock", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("material_code", "material_name")
    filter_horizontal = ("products",)


@admin.register(PackagingSupplier)
class PackagingSupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_code", "supplier_name", "phone", "is_active")
    search_fields = ("supplier_code", "supplier_name")
    filter_horizontal = ("materials_supplied",)


@admin.register(PackagingReceiving)
class PackagingReceivingAdmin(admin.ModelAdmin):
    list_display = ("receiving_number", "date", "supplier", "material", "quantity_received", "status")
    list_filter = ("status", "supplier")
    search_fields = ("receiving_number",)


@admin.register(PackagingStockLedger)
class PackagingStockLedgerAdmin(admin.ModelAdmin):
    list_display = ("material", "transaction_type", "quantity", "status", "occurred_at")
    list_filter = ("transaction_type", "status")


@admin.register(PackagingStockBalance)
class PackagingStockBalanceAdmin(admin.ModelAdmin):
    list_display = ("material", "status", "quantity")
    list_filter = ("status",)


@admin.register(FactoryPackagingStock)
class FactoryPackagingStockAdmin(admin.ModelAdmin):
    list_display = ("factory", "material", "quantity")
    list_filter = ("factory",)


@admin.register(PackingOperation)
class PackingOperationAdmin(admin.ModelAdmin):
    list_display = ("factory", "material", "product", "quantity_used", "quantity_waste", "operated_at")
    list_filter = ("factory",)


@admin.register(PackagingReconciliation)
class PackagingReconciliationAdmin(admin.ModelAdmin):
    list_display = ("material", "warehouse_qty", "factory_qty", "status", "reconciled_at")
    list_filter = ("status",)


@admin.register(SupplierEvaluation)
class SupplierEvaluationAdmin(admin.ModelAdmin):
    list_display = ("supplier", "acceptance_rate", "rejection_rate", "quality_score", "evaluated_at")
