from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models import (
    TestDefinition,
    PackingLocation,
    PackingType,
    ConformityRule,
    Grade,
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
    PlantLotSetting,
    Ton,
    RepresentativeSample,
    TonPhysicalResult,
    SampleChemicalResult,
    TonGradeAssignment,
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


@admin.register(Grade)
class GradeAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("code", "plant", "classification", "is_active")
    list_filter = ("plant", "classification", "is_active")


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
    list_display = ("reading", "conformity_rule", "grade", "quality_grade")
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


@admin.register(PlantLotSetting)
class PlantLotSettingAdmin(admin.ModelAdmin):
    list_display = ("plant", "lot_mode", "sampling_department", "current_cycle", "current_sequence", "reset_threshold")
    list_filter = ("lot_mode",)


class TonPhysicalResultInline(admin.TabularInline):
    model = TonPhysicalResult
    extra = 0


@admin.register(Ton)
class TonAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("code", "plant", "cycle_number", "sequence_number", "weight", "production_date", "production_shift")
    list_filter = ("plant", "production_date")
    readonly_fields = ("code", "cycle_number", "sequence_number")
    inlines = [TonPhysicalResultInline]


class SampleChemicalResultInline(admin.TabularInline):
    model = SampleChemicalResult
    extra = 0


@admin.register(RepresentativeSample)
class RepresentativeSampleAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("code", "plant", "cycle_number", "weight", "created_at")
    list_filter = ("plant",)
    filter_horizontal = ("tons",)
    readonly_fields = ("code", "weight")
    inlines = [SampleChemicalResultInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.refresh_derived_fields()


@admin.register(TonGradeAssignment)
class TonGradeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("ton", "grade", "assigned_by", "assigned_at")
    list_filter = ("grade",)
    readonly_fields = ("assigned_by", "assigned_at")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)