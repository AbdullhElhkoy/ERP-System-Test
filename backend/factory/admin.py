import json

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models.plant_proxy import FactoryPlant
from .models.dynamic_fields import FieldDefinition, PackingTypeField
from .services import save_final_product_rows

# استيراد الموديلات بشكل صريح لضمان معرفة Pylance بها وتجنب أخطاء "unknown import symbol"
from . import models

TestDefinition = getattr(models, "TestDefinition", None)
PackingLocation = getattr(models, "PackingLocation", None)
PackingType = getattr(models, "PackingType", None)
ConformityRule = getattr(models, "ConformityRule", None)
Grade = getattr(models, "Grade", None)
ProcessStage = getattr(models, "ProcessStage", None)
ProcessStageTest = getattr(models, "ProcessStageTest", None)
ProcessReading = getattr(models, "ProcessReading", None)
ProcessAnalysisResult = getattr(models, "ProcessAnalysisResult", None)
OutputPoint = getattr(models, "OutputPoint", None)
OutputPointTest = getattr(models, "OutputPointTest", None)
OutputReading = getattr(models, "OutputReading", None)
OutputAnalysisResult = getattr(models, "OutputAnalysisResult", None)
QualityConformityResult = getattr(models, "QualityConformityResult", None)
PackingEvent = getattr(models, "PackingEvent", None)
PackingConversion = getattr(models, "PackingConversion", None)
PlantLotSetting = getattr(models, "PlantLotSetting", None)
Ton = getattr(models, "Ton", None)
RepresentativeSample = getattr(models, "RepresentativeSample", None)
TonPhysicalResult = getattr(models, "TonPhysicalResult", None)
SampleChemicalResult = getattr(models, "SampleChemicalResult", None)
TonGradeAssignment = getattr(models, "TonGradeAssignment", None)
GradeReason = getattr(models, "GradeReason", None)
RepresentativeGroupSize = getattr(models, "RepresentativeGroupSize", None)
FloorStockBalance = getattr(models, "FloorStockBalance", None)
FloorStockMovement = getattr(models, "FloorStockMovement", None)

User = get_user_model()


@admin.register(FactoryPlant)
class FactoryPlantAdmin(admin.ModelAdmin):
    list_display = ("plant_name", "enter_button")
    search_fields = ("plant_name",)

    def enter_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Enter Factory</a>',
            f"enter/{obj.pk}/",
        )
    enter_button.short_description = "دخول المصنع"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("enter/<int:plant_id>/", self.admin_site.admin_view(self.enter_plant), name="factory_enter_plant"),
            path("dashboard/<int:plant_id>/", self.admin_site.admin_view(self.plant_dashboard), name="factory_plant_dashboard"),
            path("final-product-entry/<int:packing_type_id>/", self.admin_site.admin_view(self.final_product_entry), name="factory_final_product_entry"),
            path("settings/<int:plant_id>/", self.admin_site.admin_view(self.plant_settings), name="factory_plant_settings"),
            path("data-entry/<int:plant_id>/", self.admin_site.admin_view(self.data_entry), name="factory_data_entry"),
            path("reports/<int:plant_id>/", self.admin_site.admin_view(self.reports), name="factory_reports"),
            path("data-analysis/<int:plant_id>/", self.admin_site.admin_view(self.data_analysis), name="factory_data_analysis"),
        ]
        return custom + urls

    def _get_plant_or_redirect(self, request, plant_id):
        plant = FactoryPlant.objects.filter(pk=plant_id).first()
        if not plant:
            self.message_user(request, "المصنع غير موجود")
            return None, redirect("admin:factory_factoryplant_changelist")
        request.session["factory_current_plant_id"] = plant_id
        return plant, None

    def plant_dashboard(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error
        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "settings_url": f"/admin/factory/factoryplant/settings/{plant.pk}/",
            "data_entry_url": f"/admin/factory/factoryplant/data-entry/{plant.pk}/",
            "reports_url": f"/admin/factory/factoryplant/reports/{plant.pk}/",
            "data_analysis_url": f"/admin/factory/factoryplant/data-analysis/{plant.pk}/",
        }
        return render(request, "factory/plant_dashboard.html", context)

    def plant_settings(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error

        def admin_url(model, label):
            return f"/admin/factory/{model}/?plant_id={plant.pk}", label

        reaction_groups = [
            admin_url("processstage", "مراحل التفاعل (Process Stages)"),
        ]
        final_product_groups = [
            admin_url("packingtype", "أنواع التعبئة (Packing Types)"),
            admin_url("packinglocation", "أماكن الإنتاج (Packing Locations)"),
            admin_url("grade", "الجريد (Grades)"),
            admin_url("gradereason", "أسباب الرفض (محلي / غير مطابق)"),
            admin_url("testdefinition", "تعريفات الاختبارات (Test Definitions)"),
            admin_url("conformityrule", "قواعد المطابقة (Conformity Rules)"),
            admin_url("outputpoint", "نقاط السحب (Output Points)"),
            admin_url("representativegroupsize", "حجم مجموعة العينة الممثلة"),
            admin_url("plantlotsetting", "إعدادات الدفعات (Plant Lot Settings)"),
        ]
        final_product_groups.append((
            f"/admin/factory/packingtypefield/?plant_id={plant.pk}",
            "ربط الحقول بأنواع التعبئة (Packing Type Fields)",
        ))
        data_groups = [
            admin_url("outputreading", "قراءات السحب (Output Readings)"),
            admin_url("ton", "الأطنان (Tons)"),
            admin_url("representativesample", "العينات الممثلة (Representative Samples)"),
            admin_url("tongradeassignment", "قرارات الجريد (Ton Grade Assignments)"),
            admin_url("packingevent", "أحداث التعبئة (Packing Events)"),
            admin_url("packingconversion", "تحويلات التعبئة (Packing Conversions)"),
            admin_url("qualityconformityresult", "نتائج المطابقة (Conformity Results)"),
            admin_url("floorstockbalance", "أرصدة المخزون الأرضي (Floor Stock)"),
            admin_url("floorstockmovement", "حركات المخزون الأرضي (Floor Movements)"),
            admin_url("processreading", "قراءات التفاعل (Process Readings)"),
        ]
        company_groups = [
            ("/admin/factory/fielddefinition/", "مكتبة الحقول الديناميكية (لكل الشركة)"),
        ]

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "reaction_groups": [{"url": u, "title": t} for u, t in reaction_groups],
            "final_product_groups": [{"url": u, "title": t} for u, t in final_product_groups],
            "data_groups": [{"url": u, "title": t} for u, t in data_groups],
            "company_groups": [{"url": u, "title": t} for u, t in company_groups],
        }
        return render(request, "factory/plant_settings.html", context)

    def data_entry(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error

        reaction_stages = ProcessStage.objects.filter(plant=plant)
        final_product_packing = PackingType.objects.filter(plant=plant)

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "reaction_stages": reaction_stages,
            "final_product_packing": final_product_packing,
            "reaction_url": f"/process-reading/",
        }
        return render(request, "factory/data_entry.html", context)

    def reports(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error
        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
        }
        return render(request, "factory/reports.html", context)

    def data_analysis(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error
        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
        }
        return render(request, "factory/data_analysis.html", context)

    def enter_plant(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error
        self.message_user(request, f"دخلت مصنع: {plant.plant_name}")
        return redirect("admin:factory_plant_dashboard", plant_id=plant.pk)

    def _current_plant(self, request):
        plant_id = request.session.get("factory_current_plant_id")
        if not plant_id:
            return None
        return FactoryPlant.objects.filter(pk=plant_id).first()

    def final_product_entry(self, request, packing_type_id):
        plant = self._current_plant(request)
        if not plant:
            self.message_user(request, "لازم تدخل مصنع الأول")
            return redirect("admin:factory_factoryplant_changelist")

        packing_type = PackingType.objects.filter(pk=packing_type_id, plant=plant).first()
        if not packing_type:
            self.message_user(request, "نوع التعبئة غير موجود لهذا المصنع")
            return redirect("admin:factory_factoryplant_changelist")

        if request.method == "POST":
            return self._save_final_product_entry(request, plant, packing_type)

        chemical_tests = TestDefinition.objects.filter(plant=plant, category="chemical", scope="final_product")
        physical_tests = TestDefinition.objects.filter(plant=plant, category="physical", scope="final_product")
        grades = Grade.objects.filter(plant=plant, is_active=True)
        
        local_reasons = GradeReason.objects.filter(plant=plant, reason_type="local")
        non_conforming_reasons = GradeReason.objects.filter(plant=plant, reason_type="non_conforming")

        lot_setting, _ = PlantLotSetting.objects.get_or_create(plant=plant)
        group_size_setting = RepresentativeGroupSize.objects.filter(plant=plant, packing_type=packing_type).first()
        default_group_size = group_size_setting.default_group_size if group_size_setting else 4

        users_list = list(User.objects.filter(is_staff=True).values("id", "first_name", "last_name", "username"))
        formatted_users = [
            {
                "id": u["id"], 
                "name": f"{u['first_name']} {u['last_name']}".strip() or u["username"]
            } for u in users_list
        ]

        locations = PackingLocation.objects.filter(plant=plant)

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "packing_type": packing_type,
            "packing_type_id": packing_type.pk,            "chemical_tests": chemical_tests,
            "physical_tests": physical_tests,
            "grades": grades,
            "chemical_tests_json": [{"id": getattr(t, "pk", getattr(t, "id", None)), "name": t.name} for t in chemical_tests],
            "physical_tests_json": [{"id": getattr(t, "pk", getattr(t, "id", None)), "name": t.name} for t in physical_tests],
            "grades_json": [
                {
                    "id": getattr(g, "pk", getattr(g, "id", None)),
                    "code": g.code,
                    "classification": getattr(g.classification, "code", str(g.classification)),
                }
                for g in grades
            ],
            "local_reasons_json": [{"id": getattr(r, "pk", getattr(r, "id", None)), "text": r.text} for r in local_reasons],
            "non_conforming_reasons_json": [{"id": getattr(r, "pk", getattr(r, "id", None)), "text": r.text} for r in non_conforming_reasons],
            "users_json": formatted_users,
            "packing_locations_json": [{"id": getattr(l, "pk", getattr(l, "id", None)), "name": l.name} for l in locations],
            "shift_choices": ["A", "B", "C", "D"],
            "next_cycle": lot_setting.current_cycle,
            "next_sequence": lot_setting.current_sequence + 1,
            "default_group_size": default_group_size,
        }
        return render(request, "factory/final_product_entry.html", context)

    def _save_final_product_entry(self, request, plant, packing_type):
        payload = json.loads(request.body)
        rows = payload.get("rows", [])
        saved_count = save_final_product_rows(plant, packing_type, rows, request.user)
        return JsonResponse({"status": "ok", "rows_saved": saved_count})


@admin.register(TestDefinition)
class TestDefinitionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant", "category", "scope", "unit")
    list_filter = ("plant", "category", "scope")


@admin.register(PackingLocation)
class PackingLocationAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant")
    list_filter = ("plant",)

class PackingTypeFieldInline(admin.TabularInline):
    model = PackingTypeField
    extra = 1
    autocomplete_fields = ["field"]


@admin.register(PackingType)
class PackingTypeAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant")
    list_filter = ("plant",)
    inlines = [PackingTypeFieldInline]


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

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj is not None:
            formset.form.base_fields["test"].queryset = TestDefinition.objects.filter(
                plant=obj.plant, scope=TestDefinition.SCOPE_REACTION
            )
        return formset


@admin.register(ProcessStage)
class ProcessStageAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("order", "name", "code", "test_count", "is_active", "plant")
    list_editable = ("order", "is_active")
    list_filter = ("plant", "is_active")
    ordering = ("plant", "order", "pk")
    inlines = [ProcessStageTestInline]

    def test_count(self, obj):
        return obj.stage_tests.count()
    test_count.short_description = "عدد الاختبارات"


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
class QualityConformityResultAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "reading__plant"
    list_display = ("reading", "conformity_rule", "grade", "quality_grade")
    list_filter = ("quality_grade",)

    def plant(self, obj):
        return obj.reading.plant if obj.reading else None
    plant.short_description = "المصنع"


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
class PlantLotSettingAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "lot_mode", "sampling_department", "current_cycle", "current_sequence", "reset_threshold")
    list_filter = ("plant", "lot_mode")


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
class TonGradeAssignmentAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "ton__plant"
    list_display = ("ton", "grade", "reason", "assigned_by", "assigned_at")
    list_filter = ("grade", "reason")
    readonly_fields = ("assigned_by", "assigned_at")

    def plant(self, obj):
        return obj.ton.plant if obj.ton else None
    plant.short_description = "المصنع"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GradeReason)
class GradeReasonAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("text", "reason_type", "plant")
    list_filter = ("plant", "reason_type")


@admin.register(RepresentativeGroupSize)
class RepresentativeGroupSizeAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "packing_type", "default_group_size")
    list_filter = ("plant", "packing_type")


@admin.register(FieldDefinition)
class FieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "field_type", "category", "unit", "is_active")
    list_filter = ("category", "field_type", "is_active")
    search_fields = ("name", "key")
    prepopulated_fields = {"key": ("name",)}


@admin.register(PackingTypeField)
class PackingTypeFieldAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "packing_type__plant"
    list_display = ("packing_type", "field", "order", "is_required")
    list_filter = ("packing_type", "field__category")


@admin.register(FloorStockBalance)
class FloorStockBalanceAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "grade", "quantity", "updated_at")
    list_filter = ("plant", "grade")
    readonly_fields = ("quantity", "updated_at")


@admin.register(FloorStockMovement)
class FloorStockMovementAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "grade", "movement_type", "quantity", "ton", "occurred_at")
    list_filter = ("plant", "grade", "movement_type")
    search_fields = ("ton__code",)