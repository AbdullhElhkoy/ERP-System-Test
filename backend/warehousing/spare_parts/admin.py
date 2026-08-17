from django.contrib import admin
from .models import (
    SparePartItem, SparePartStockTransaction, SparePartStockBalance,
    ReceivingVoucher, IssueVoucher, StockCount,
)


@admin.register(SparePartItem)
class SparePartItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "item_name", "category", "plant", "minimum_stock", "is_active")
    list_filter = ("plant", "is_active")
    search_fields = ("item_code", "item_name")


@admin.register(SparePartStockTransaction)
class SparePartStockTransactionAdmin(admin.ModelAdmin):
    list_display = ("item", "transaction_type", "quantity", "occurred_at")
    list_filter = ("transaction_type",)


@admin.register(SparePartStockBalance)
class SparePartStockBalanceAdmin(admin.ModelAdmin):
    list_display = ("item", "total_stock", "available", "on_loan", "in_maintenance")


@admin.register(ReceivingVoucher)
class ReceivingVoucherAdmin(admin.ModelAdmin):
    list_display = ("voucher_number", "date", "supplier_name", "item", "quantity", "status")
    list_filter = ("status",)


@admin.register(IssueVoucher)
class IssueVoucherAdmin(admin.ModelAdmin):
    list_display = ("voucher_number", "date", "issued_to", "item", "quantity", "status")
    list_filter = ("status",)


@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
    list_display = ("item", "count_date", "system_quantity", "physical_quantity", "variance")
    list_filter = ("item",)
