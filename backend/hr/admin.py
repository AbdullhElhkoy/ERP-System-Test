from django.contrib import admin
from .models import (
    HREmployeeProfile, Attendance, Leave, LeaveBalance,
    Contract, Discipline, Training,
)


@admin.register(HREmployeeProfile)
class HREmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee", "plant", "department", "job_title", "contract_type", "status")
    list_filter = ("plant", "department", "status", "contract_type")
    search_fields = ("employee__full_name", "job_title", "section")
    raw_id_fields = ("employee", "plant", "department", "direct_manager", "shift")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "plant", "check_in", "check_out", "is_late", "late_minutes", "overtime_hours", "is_absent")
    list_filter = ("plant", "date", "is_absent", "is_late")
    search_fields = ("employee__full_name",)
    date_hierarchy = "date"
    raw_id_fields = ("employee", "plant", "shift")


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ("employee", "plant", "leave_type", "start_date", "end_date", "days", "status")
    list_filter = ("plant", "leave_type", "status")
    search_fields = ("employee__full_name",)
    date_hierarchy = "start_date"
    raw_id_fields = ("employee", "plant", "approved_by")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "year", "entitled", "taken", "remaining")
    list_filter = ("leave_type", "year")
    search_fields = ("employee__full_name",)
    raw_id_fields = ("employee",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("employee", "plant", "contract_type", "start_date", "end_date", "salary", "status")
    list_filter = ("plant", "contract_type", "status")
    search_fields = ("employee__full_name",)
    date_hierarchy = "start_date"
    raw_id_fields = ("employee", "plant")


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("employee", "plant", "violation_type", "action_type", "date", "issued_by")
    list_filter = ("plant", "action_type")
    search_fields = ("employee__full_name", "violation_type")
    date_hierarchy = "date"
    raw_id_fields = ("employee", "plant", "issued_by")


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ("employee", "plant", "training_name", "provider", "start_date", "end_date", "has_certificate")
    list_filter = ("plant", "has_certificate")
    search_fields = ("employee__full_name", "training_name", "provider")
    date_hierarchy = "start_date"
    raw_id_fields = ("employee", "plant")
