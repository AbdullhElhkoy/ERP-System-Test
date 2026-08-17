from django.contrib import admin
from .models import (
    Customer, SalesPriceList, Quotation, QuotationLine,
    SalesOrder, SalesOrderLine,
    OrderPlantAllocation, OrderPlantAllocationChangeLog, OrderMovement,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_code", "customer_name", "phone", "credit_limit", "status")
    search_fields = ("customer_code", "customer_name")
    list_filter = ("status",)


@admin.register(SalesPriceList)
class SalesPriceListAdmin(admin.ModelAdmin):
    list_display = ("product", "packaging_type", "price", "currency", "valid_from", "valid_to")
    list_filter = ("currency",)


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 1


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("quotation_number", "customer", "status", "valid_until", "created_at")
    list_filter = ("status",)
    search_fields = ("quotation_number",)
    inlines = [QuotationLineInline]


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer_name", "status", "total_quantity", "created_at")
    list_filter = ("status", "grade_policy", "batch_source")
    search_fields = ("order_number", "customer_name")
    inlines = [SalesOrderLineInline]


@admin.register(OrderPlantAllocation)
class OrderPlantAllocationAdmin(admin.ModelAdmin):
    list_display = ("order", "plant", "allocated_quantity")
    list_filter = ("plant",)


@admin.register(OrderPlantAllocationChangeLog)
class OrderPlantAllocationChangeLogAdmin(admin.ModelAdmin):
    list_display = ("order", "from_plant", "to_plant", "quantity", "changed_at")
    list_filter = ("from_plant", "to_plant")


@admin.register(OrderMovement)
class OrderMovementAdmin(admin.ModelAdmin):
    list_display = ("order", "movement_type", "quantity", "source_plant", "occurred_at")
    list_filter = ("movement_type",)
