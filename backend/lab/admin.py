from django.contrib import admin
from .models import Sample, SampleGroup, SampleRequiredTest, SampleTestResult


@admin.register(SampleGroup)
class SampleGroupAdmin(admin.ModelAdmin):
    list_display = ("group_code", "plant", "location_label", "packing_type_name", "is_open", "created_at")
    list_filter = ("plant", "is_open")
    search_fields = ("group_code", "location_label")


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("sample_code", "source_type", "plant", "status", "collected_at", "created_at")
    list_filter = ("source_type", "plant", "status")
    search_fields = ("sample_code",)
    readonly_fields = ("created_at",)


@admin.register(SampleRequiredTest)
class SampleRequiredTestAdmin(admin.ModelAdmin):
    list_display = ("sample", "test_name", "is_completed")
    list_filter = ("is_completed", "sample__source_type")


@admin.register(SampleTestResult)
class SampleTestResultAdmin(admin.ModelAdmin):
    list_display = ("sample", "test_name", "result", "entered_by", "entered_at")
    list_filter = ("sample__status",)
