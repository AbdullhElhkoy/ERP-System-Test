import json

from django import forms
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
            path("data/<int:plant_id>/", self.admin_site.admin_view(self.data), name="factory_data"),
            path("data-packings/<int:packing_type_id>/", self.admin_site.admin_view(self.data_packings), name="factory_data_packings"),
            path("data-reading/<int:reading_id>/", self.admin_site.admin_view(self.data_reading), name="factory_data_reading"),
            path("data-reaction-readings/<int:stage_id>/", self.admin_site.admin_view(self.data_reaction_readings), name="factory_data_reaction_readings"),
            path("data-reaction-reading/<int:reading_id>/", self.admin_site.admin_view(self.data_reaction_reading), name="factory_data_reaction_reading"),
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
            "data_url": f"/admin/factory/factoryplant/data/{plant.pk}/",
            "reports_url": f"/admin/factory/factoryplant/reports/{plant.pk}/",
            "data_analysis_url": f"/admin/factory/factoryplant/data-analysis/{plant.pk}/",
        }
        return render(request, "factory/plant_dashboard.html", context)

    def plant_settings(self, request, plant_id):
        plant, error = self._get_plant_or_redirect(request, plant_id)
        if error:
            return error

        def admin_url(model, label):
            return f"/admin/factory/{model}/", label

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
            "/admin/factory/packingtypefield/",
            "ربط الحقول بأنواع التعبئة (Packing Type Fields)",
        ))
        locked_spec = ("#", "المواصفة (معطلة حالياً)")
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
            "final_product_groups": [
                *[{"url": u, "title": t} for u, t in final_product_groups],
                {"url": locked_spec[0], "title": locked_spec[1], "locked": True},
            ],
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
            "reaction_url": f"/factory/process-reading/",
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

    def data(self, request, plant_id):
        """صفحة داتا: اختيار مرحلة تفاعل أو نوع تعبئة (بنفس تقسيم الإدخال) لعرض/تعديل البيانات السابقة."""
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
        }
        return render(request, "factory/data.html", context)

    def data_packings(self, request, packing_type_id):
        """قائمة القراءات السابقة لنوع تعبئة محدد."""
        plant = self._current_plant(request)
        if not plant:
            self.message_user(request, "لازم تدخل مصنع الأول")
            return redirect("admin:factory_factoryplant_changelist")

        packing_type = PackingType.objects.filter(pk=packing_type_id, plant=plant).first()
        if not packing_type:
            self.message_user(request, "نوع التعبئة غير موجود لهذا المصنع")
            return redirect("admin:factory_data", plant_id=plant.pk)

        readings = (
            OutputReading.objects.filter(plant=plant, packing_type=packing_type)
            .select_related("output_point", "packing_location", "sampled_by", "analyzed_by", "lab_shift_head", "reviewed_by")
            .order_by("-sampled_at")
        )

        reading_summaries = []
        for reading in readings:
            tons = list(reading.tons.all())
            assignments = TonGradeAssignment.objects.filter(ton__in=tons) if tons else []
            grade_text = ""
            if assignments:
                codes = [f"{a.primary_grade.code}" + (f"/{a.secondary_grade.code}" if a.secondary_grade else "") for a in assignments]
                grade_text = ", ".join(sorted(set(codes)))
            reading_summaries.append({
                "reading": reading,
                "ton_count": len(tons),
                "total_weight": sum((t.weight for t in tons), __import__("decimal").Decimal("0")),
                "grade_text": grade_text,
            })

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "packing_type": packing_type,
            "reading_summaries": reading_summaries,
        }
        return render(request, "factory/data_packings.html", context)

    def data_reading(self, request, reading_id):
        """عرض/تعديل قراءة واحدة سابقة. لا إضافة من هنا."""
        plant = self._current_plant(request)
        if not plant:
            self.message_user(request, "لازم تدخل مصنع الأول")
            return redirect("admin:factory_factoryplant_changelist")

        reading = OutputReading.objects.filter(pk=reading_id, plant=plant).select_related(
            "output_point", "packing_location", "packing_type", "sampled_by", "analyzed_by", "lab_shift_head", "reviewed_by"
        ).first()
        if not reading:
            self.message_user(request, "القراءة غير موجودة")
            return redirect("admin:factory_data", plant_id=plant.pk)

        from .data_grid import build_reading_grid, save_reading_edits

        if request.method == "POST":
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)
            errors = save_reading_edits(plant, reading, payload.get("rows", []), request.user)
            if errors:
                return JsonResponse({"status": "error", "message": "; ".join(errors)}, status=400)
            return JsonResponse({"status": "ok"})

        grid = build_reading_grid(reading)
        users_list = list(User.objects.filter(is_staff=True).values("id", "first_name", "last_name", "username"))
        formatted_users = [
            {
                "id": u["id"],
                "name": f"{u['first_name']} {u['last_name']}".strip() or u["username"]
            } for u in users_list
        ]
        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "packing_type": reading.packing_type,
            "reading": reading,
            "grid": grid,
            "chemical_tests": grid["chemical_tests"],
            "physical_tests": grid["physical_tests"],
            "chemical_tests_json": json.dumps([{"id": t.id, "name": t.name} for t in grid["chemical_tests"]], ensure_ascii=False),
            "physical_tests_json": json.dumps([{"id": t.id, "name": t.name} for t in grid["physical_tests"]], ensure_ascii=False),
            "packing_locations": list(PackingLocation.objects.filter(plant=plant)),
            "shift_choices": ["A", "B", "C", "D"],
            "users": formatted_users,
        }
        return render(request, "factory/data_reading.html", context)

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

    def data_reaction_readings(self, request, stage_id):
        """قائمة قراءات التفاعل السابقة لمرحلة محددة."""
        plant = self._current_plant(request)
        if not plant:
            self.message_user(request, "لازم تدخل مصنع الأول")
            return redirect("admin:factory_factoryplant_changelist")

        stage = ProcessStage.objects.filter(pk=stage_id, plant=plant).first()
        if not stage:
            self.message_user(request, "المرحلة غير موجودة لهذا المصنع")
            return redirect("admin:factory_data", plant_id=plant.pk)

        readings = ProcessReading.objects.filter(plant=plant, stage=stage).prefetch_related("results").order_by("-sampled_at")

        reading_summaries = []
        for reading in readings:
            results_text = ", ".join(
                f"{r.test.name}: {r.result}" for r in reading.results.all().select_related("test")
            )
            reading_summaries.append({
                "reading": reading,
                "results_text": results_text,
            })

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "stage": stage,
            "reading_summaries": reading_summaries,
        }
        return render(request, "factory/data_reaction_readings.html", context)

    def data_reaction_reading(self, request, reading_id):
        """عرض/تعديل قراءة تفاعل واحدة سابقة. لا إضافة من هنا."""
        plant = self._current_plant(request)
        if not plant:
            self.message_user(request, "لازم تدخل مصنع الأول")
            return redirect("admin:factory_factoryplant_changelist")

        reading = ProcessReading.objects.filter(pk=reading_id, plant=plant).select_related("stage").first()
        if not reading:
            self.message_user(request, "القراءة غير موجودة")
            return redirect("admin:factory_data", plant_id=plant.pk)

        tests = TestDefinition.objects.filter(
            plant=plant, scopes__contains=[TestDefinition.SCOPE_REACTION]
        ).order_by("id")

        if request.method == "POST":
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)

            notes = payload.get("notes", reading.notes)
            sampled_at_raw = payload.get("sampled_at") or reading.sampled_at.strftime("%Y-%m-%dT%H:%M")
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(sampled_at_raw)
            reading.sampled_at = parsed or reading.sampled_at
            reading.notes = notes
            reading.save()

            result_map = payload.get("results", {})
            for test in tests:
                val_raw = result_map.get(str(test.pk))
                existing = ProcessAnalysisResult.objects.filter(reading=reading, test=test).first()
                if val_raw in (None, ""):
                    if existing:
                        existing.delete()
                    continue
                try:
                    from decimal import Decimal, InvalidOperation
                    val = Decimal(str(val_raw))
                    ProcessAnalysisResult.objects.update_or_create(
                        reading=reading, test=test, defaults={"result": val}
                    )
                except (InvalidOperation, ValueError):
                    continue

            return JsonResponse({"status": "ok"})

        results = {
            r.test_id: (str(r.result) if r.result is not None else "")
            for r in ProcessAnalysisResult.objects.filter(reading=reading).select_related("test")
        }

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
            "reading": reading,
            "tests": tests,
            "results": results,
            "tests_json": json.dumps([{"id": t.id, "name": t.name, "unit": t.unit or ""} for t in tests], ensure_ascii=False),
        }
        return render(request, "factory/data_reaction_reading.html", context)

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

        chemical_tests = TestDefinition.objects.filter(plant=plant, category="chemical", scopes__contains=[TestDefinition.SCOPE_FINAL_PRODUCT])
        physical_tests = TestDefinition.objects.filter(plant=plant, category="physical", scopes__contains=[TestDefinition.SCOPE_FINAL_PRODUCT])
        grades = Grade.objects.filter(plant=plant, is_active=True)
        primary_grades = grades.filter(grade_type=Grade.TYPE_PRIMARY)
        secondary_grades = grades.filter(grade_type=Grade.TYPE_SECONDARY)
        
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

        dynamic_fields_list = []
        configs = PackingTypeField.objects.filter(packing_type=packing_type, field__is_active=True).select_related("field")
        for cfg in configs:
            f = cfg.field
            dynamic_fields_list.append({
                "id": f.id,
                "key": f.key,
                "name": f.name,
                "field_type": f.field_type,
                "unit": f.unit,
                "choices": f.choices or [],
                "is_required": cfg.is_required,
            })

        context = {
            **self.admin_site.each_context(request),
            "plant": plant,
            "packing_type": packing_type,
            "packing_type_id": packing_type.pk,            "chemical_tests": chemical_tests,
            "physical_tests": physical_tests,
            "grades": grades,
            "chemical_tests_json": [{"id": getattr(t, "pk", getattr(t, "id", None)), "name": t.name} for t in chemical_tests],
            "physical_tests_json": [{"id": getattr(t, "pk", getattr(t, "id", None)), "name": t.name} for t in physical_tests],
            "primary_grades_json": [
                {
                    "id": getattr(g, "pk", getattr(g, "id", None)),
                    "code": g.code,
                }
                for g in primary_grades
            ],
            "secondary_grades_json": [
                {
                    "id": getattr(g, "pk", getattr(g, "id", None)),
                    "code": g.code,
                }
                for g in secondary_grades
            ],
            "grades_json": [
                {
                    "id": getattr(g, "pk", getattr(g, "id", None)),
                    "code": g.code,
                    "grade_type": g.grade_type,
                }
                for g in grades
            ],
            "local_reasons_json": [{"id": getattr(r, "pk", getattr(r, "id", None)), "text": r.text} for r in local_reasons],
            "non_conforming_reasons_json": [{"id": getattr(r, "pk", getattr(r, "id", None)), "text": r.text} for r in non_conforming_reasons],
            "users_json": formatted_users,
            "packing_locations_json": [{"id": getattr(l, "pk", getattr(l, "id", None)), "name": l.name} for l in locations],
            "dynamic_fields_json": dynamic_fields_list,
            "shift_choices": ["A", "B", "C", "D"],
            "next_cycle": lot_setting.current_cycle,
            "next_sequence": lot_setting.current_sequence + 1,
            "default_group_size": default_group_size,
        }
        return render(request, "factory/final_product_entry.html", context)

    def _save_final_product_entry(self, request, plant, packing_type):
        try:
            payload = json.loads(request.body)
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)
        rows = payload.get("rows", [])
        try:
            saved_count = save_final_product_rows(plant, packing_type, rows, request.user)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء الحفظ: {e}"}, status=500)
        return JsonResponse({"status": "ok", "rows_saved": saved_count})


class TestDefinitionForm(forms.ModelForm):
    scopes = forms.MultipleChoiceField(
        choices=TestDefinition.SCOPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="النطاقات",
    )

    class Meta:
        model = TestDefinition
        fields = "__all__"


@admin.register(TestDefinition)
class TestDefinitionAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("name", "plant", "category", "scopes_display", "unit")
    list_filter = ("plant", "category")
    form = TestDefinitionForm
    fieldsets = (
        (None, {"fields": ("plant", "name", "category", "unit")}),
        ("النطاقات (يمكن اختيار أكثر من واحدة)", {"fields": ("scopes",), "classes": ("wide",)}),
    )


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
    list_display = ("code", "grade_type", "is_active", "plant")
    list_filter = ("plant", "grade_type", "is_active")
    list_editable = ("is_active",)
    search_fields = ("code",)


class ProcessStageTestInline(admin.TabularInline):
    model = ProcessStageTest
    extra = 1

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj is not None:
            formset.form.base_fields["test"].queryset = TestDefinition.objects.filter(
                plant=obj.plant, scopes__contains=[TestDefinition.SCOPE_REACTION]
            )
        return formset


@admin.register(ProcessStage)
class ProcessStageAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("order", "name", "code", "test_count", "is_active", "plant")
    list_display_links = ("name",)
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
    list_display = ("ton", "primary_grade", "secondary_grade", "reason", "assigned_by", "assigned_at")
    list_filter = ("primary_grade", "secondary_grade", "reason")
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
    list_display = ("plant", "grade", "status", "quantity", "updated_at")
    list_filter = ("plant", "grade", "status")
    readonly_fields = ("quantity", "updated_at")


@admin.register(FloorStockMovement)
class FloorStockMovementAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("plant", "grade", "status", "movement_type", "quantity", "ton", "occurred_at")
    list_filter = ("plant", "grade", "status", "movement_type")
    search_fields = ("ton__code",)