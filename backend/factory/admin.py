from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models import (
    TestDefinition,
    PackingLocation,
    PackingType,
    ConformityRule,
    ProcessStage,
    ProcessStageTest,
    ProcessReading,
    ProcessAnalysisResult,
    OutputPoint,
    OutputPointTest,
    OutputReading,
    OutputAnalysisResult,
    QualityConformityResult,
    PackingEvent,
    PackingConversion,
)


@admin.register(TestDefinition)
class TestDefinitionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant", "category", "unit")
    list_filter = ("plant", "category")


@admin.register(PackingLocation)
class PackingLocationAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant")
    list_filter = ("plant",)


@admin.register(PackingType)
class PackingTypeAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant")
    list_filter = ("plant",)


@admin.register(ConformityRule)
class ConformityRuleAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant", "quality_grade")
    list_filter = ("plant", "quality_grade")


class ProcessStageTestInline(admin.TabularInline):
    model = ProcessStageTest
    extra = 1


@admin.register(ProcessStage)
class ProcessStageAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("code", "name", "plant")
    list_filter = ("plant",)
    inlines = [ProcessStageTestInline]


class ProcessAnalysisResultInline(admin.TabularInline):
    model = ProcessAnalysisResult
    extra = 0


@admin.register(ProcessReading)
class ProcessReadingAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("stage", "plant", "sampled_at")
    list_filter = ("plant", "stage")
    inlines = [ProcessAnalysisResultInline]


class OutputPointTestInline(admin.TabularInline):
    model = OutputPointTest
    extra = 1


@admin.register(OutputPoint)
class OutputPointAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("code", "name", "plant")
    list_filter = ("plant",)
    inlines = [OutputPointTestInline]


class OutputAnalysisResultInline(admin.TabularInline):
    model = OutputAnalysisResult
    extra = 0


@admin.register(OutputReading)
class OutputReadingAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("sample_code", "output_point", "plant", "sampled_at", "shift", "packing_location", "packing_type")
    list_filter = ("plant", "output_point", "shift")
    inlines = [OutputAnalysisResultInline]


@admin.register(QualityConformityResult)
class QualityConformityResultAdmin(admin.ModelAdmin):
    list_display = ("reading", "conformity_rule", "quality_grade")
    list_filter = ("quality_grade",)


@admin.register(PackingEvent)
class PackingEventAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("output_reading", "packing_type", "quantity", "unit", "packed_at")
    list_filter = ("plant", "packing_type")


@admin.register(PackingConversion)
class PackingConversionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("source_event", "target_packing_type", "quantity", "unit", "converted_at")
    list_filter = ("plant", "target_packing_type")