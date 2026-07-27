from django.contrib import admin
from .models import (
    Employee,
    EmployeeAssignment,
    ShiftType,
    ShiftGroup,
    ShiftRotationPattern,
    RotationReference,
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'national_id', 'phone', 'hire_date', 'is_active')
    search_fields = ('full_name', 'national_id', 'phone')
    list_filter = ('is_active',)


@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'employee', 'position', 'shift_mode', 'group', 'fixed_shift_type', 'start_date', 'is_current')
    list_filter = ('shift_mode', 'is_current', 'group')
    search_fields = ('employee__full_name',)


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ('shift_type_id', 'shift_type_name', 'start_time', 'end_time')


@admin.register(ShiftGroup)
class ShiftGroupAdmin(admin.ModelAdmin):
    list_display = ('group_id', 'group_name')


@admin.register(ShiftRotationPattern)
class ShiftRotationPatternAdmin(admin.ModelAdmin):
    list_display = ('group', 'day_offset', 'shift_type')
    list_filter = ('group',)
    ordering = ('group', 'day_offset')


@admin.register(RotationReference)
class RotationReferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'reference_date')