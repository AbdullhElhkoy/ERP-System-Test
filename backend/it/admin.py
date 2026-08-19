from django.contrib import admin
from .models import AssetCategory, ITAsset, EmployeeAccount, AssetHandover, ITClearance


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ITAsset)
class ITAssetAdmin(admin.ModelAdmin):
    list_display = ("asset_code", "category", "brand", "model_name", "serial_number", "status", "plant", "assigned_to")
    list_filter = ("status", "category", "plant")
    search_fields = ("asset_code", "serial_number", "brand", "model_name")
    raw_id_fields = ("plant", "department", "assigned_to")


@admin.register(EmployeeAccount)
class EmployeeAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "employee", "plant", "department", "login_method", "status", "last_login_at")
    list_filter = ("status", "login_method", "plant")
    search_fields = ("username", "employee__full_name")
    raw_id_fields = ("employee", "user", "plant", "department", "created_by")


@admin.register(AssetHandover)
class AssetHandoverAdmin(admin.ModelAdmin):
    list_display = ("asset", "employee", "handover_type", "handover_date", "condition_at_handover", "performed_by")
    list_filter = ("handover_type",)
    search_fields = ("asset__asset_code", "employee__full_name")
    date_hierarchy = "handover_date"
    raw_id_fields = ("asset", "employee", "performed_by")


@admin.register(ITClearance)
class ITClearanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "status", "accounts_disabled", "assets_returned", "clearance_date", "performed_by")
    list_filter = ("status", "accounts_disabled", "assets_returned")
    search_fields = ("employee__full_name",)
    raw_id_fields = ("employee", "performed_by")
