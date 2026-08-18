from django.contrib import admin
from .models import Product, StockLedger, StockBalance


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_code", "product_name", "product_type", "is_active")
    list_filter = ("is_active",)
    search_fields = ("product_code", "product_name")
    filter_horizontal = ("plants", "packing_types")


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ("product", "plant", "packaging_type", "transaction_type", "quantity", "occurred_at")
    list_filter = ("transaction_type", "plant", "product")
    readonly_fields = ("created_at",)


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("plant", "product", "packaging_type", "total_stock", "reserved", "available", "qc_hold")
    list_filter = ("plant", "product")
