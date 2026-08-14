import json
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model

from plants.models import Plant
from .models import (
    ProcessStage,
    TestDefinition,
    ProcessReading,
    ProcessAnalysisResult,
    PlantLotSetting,
    RepresentativeGroupSize,
    GradeReason,
    PackingType,
    PackingLocation,
    Grade,
    FieldDefinition,
    PackingTypeField,
)
from .services import save_final_product_rows

User = get_user_model()


@staff_member_required
def process_reading_grid(request):
    plant_id = request.session.get("factory_current_plant_id")
    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
    if not plant:
        messages.error(request, "لازم تدخل مصنع الأول")
        return redirect("admin:factory_factoryplant_changelist")
    stages = ProcessStage.objects.filter(plant=plant, is_active=True)
    tests = TestDefinition.objects.filter(plant=plant, scope=TestDefinition.SCOPE_REACTION)

    if request.method == "POST":
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                rows = data.get("rows", [])
                with transaction.atomic():
                    saved_count = 0
                    for row in rows:
                        sampled_at_raw = row.get("sampled_at") or row.get("production_date")
                        sampled_at = parse_datetime(sampled_at_raw) if sampled_at_raw else None
                        stage_id = row.get("stage_id")
                        stage = ProcessStage.objects.filter(pk=stage_id, plant=plant).first() if stage_id else None
                        if not stage:
                            continue
                        reading = ProcessReading.objects.create(
                            plant=plant,
                            stage=stage,
                            sampled_at=sampled_at or timezone.now(),
                            notes=row.get("notes", ""),
                        )
                        test_results = {**row.get("chemical", {}), **row.get("physical", {})}
                        for test_id, val_raw in test_results.items():
                            if val_raw != "" and val_raw is not None:
                                try:
                                    test_obj = TestDefinition.objects.get(pk=test_id, plant=plant)
                                    ProcessAnalysisResult.objects.create(
                                        reading=reading,
                                        test=test_obj,
                                        result=Decimal(str(val_raw)),
                                    )
                                except (TestDefinition.DoesNotExist, InvalidOperation):
                                    continue
                        saved_count += 1
                return JsonResponse({"status": "ok", "rows_saved": saved_count})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        selected_stage_ids = [int(s) for s in request.POST.getlist("stages")]
        selected_stages = ProcessStage.objects.filter(plant=plant, pk__in=selected_stage_ids)
        sampled_at = parse_datetime(request.POST.get("sampled_at")) or timezone.now()

        with transaction.atomic():
            for stage in selected_stages:
                reading = ProcessReading.objects.create(plant=plant, stage=stage, sampled_at=sampled_at)
                for test in tests:
                    cell_key = f"cell_{stage.pk}_{test.pk}"
                    val_raw = request.POST.get(cell_key)
                    if val_raw:
                        try:
                            ProcessAnalysisResult.objects.create(
                                reading=reading, test=test, result=Decimal(val_raw)
                            )
                        except InvalidOperation:
                            continue
        messages.success(request, "تم حفظ القراءات بنجاح")
        return redirect(request.path)

    selected_stage_ids = [int(s) for s in request.GET.getlist("stages")]
    selected_stages = ProcessStage.objects.filter(plant=plant, pk__in=selected_stage_ids)

    stages_json = json.dumps(
        [{"id": s.pk, "name": s.name, "order": s.order} for s in stages],
        ensure_ascii=False,
    )
    tests_json = json.dumps(
        [
            {
                "id": t.pk,
                "name": t.name,
                "category": t.category,
                "unit": t.unit,
            }
            for t in tests
        ],
        ensure_ascii=False,
    )

    context = {
        "plant": plant,
        "stages": stages,
        "tests": tests,
        "stages_json": stages_json,
        "tests_json": tests_json,
        "selected_stage_ids": selected_stage_ids,
        "selected_stages": selected_stages,
        "dashboard_url": f"/admin/factory/factoryplant/dashboard/{plant.pk}/",
    }
    return render(request, "factory/process_reading_grid.html", context)


@staff_member_required
def final_product_entry_grid(request, plant_id, packing_slug):
    plant = get_object_or_404(Plant, pk=plant_id)

    packing_type = None
    for pt in PackingType.objects.filter(plant=plant):
        if slugify(pt.name) == packing_slug:
            packing_type = pt
            break

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            rows = data.get("rows", [])
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "بيانات غير صالحة"}, status=400)

        try:
            saved_count = save_final_product_rows(plant, packing_type, rows, request.user)
            return JsonResponse({"status": "ok", "rows_saved": saved_count})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    chemical_tests = TestDefinition.objects.filter(
        plant=plant, category=TestDefinition.CATEGORY_CHEMICAL, scope=TestDefinition.SCOPE_FINAL_PRODUCT
    )
    physical_tests = TestDefinition.objects.filter(
        plant=plant, category=TestDefinition.CATEGORY_PHYSICAL, scope=TestDefinition.SCOPE_FINAL_PRODUCT
    )

    lot_setting, _ = PlantLotSetting.objects.get_or_create(plant=plant)

    default_group_size = 4
    if packing_type:
        size_setting = RepresentativeGroupSize.objects.filter(plant=plant, packing_type=packing_type).first()
        if size_setting:
            default_group_size = size_setting.default_group_size

    grades_list = [
        {
            "id": g.id,
            "code": g.code,
            "classification": getattr(g.classification, "code", str(g.classification)),
        }
        for g in Grade.objects.filter(plant=plant, is_active=True)
    ]

    local_reasons_list = list(
        GradeReason.objects.filter(plant=plant, reason_type=GradeReason.REASON_LOCAL).values("id", "text")
    )
    non_conforming_list = list(
        GradeReason.objects.filter(plant=plant, reason_type=GradeReason.REASON_NON_CONFORMING).values("id", "text")
    )
    users_list = [
        {"id": u.id, "name": u.get_full_name() or u.username}
        for u in User.objects.filter(is_active=True).order_by("username")
    ]
    locations_list = list(PackingLocation.objects.filter(plant=plant).values("id", "name"))

    dynamic_fields_list = []
    if packing_type:
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
        "plant": plant,
        "packing_type": packing_type,
        "packing_slug": packing_slug,
        "chemical_tests": chemical_tests,
        "physical_tests": physical_tests,
        "chemical_tests_json": json.dumps(list(chemical_tests.values("id", "name")), ensure_ascii=False),
        "physical_tests_json": json.dumps(list(physical_tests.values("id", "name")), ensure_ascii=False),
        "grades_json": json.dumps(grades_list, ensure_ascii=False),
        "local_reasons_json": json.dumps(local_reasons_list, ensure_ascii=False),
        "non_conforming_reasons_json": json.dumps(non_conforming_list, ensure_ascii=False),
        "users_json": json.dumps(users_list, ensure_ascii=False),
        "packing_locations_json": json.dumps(locations_list, ensure_ascii=False),
        "dynamic_fields_json": json.dumps(dynamic_fields_list, ensure_ascii=False),
        "next_cycle": lot_setting.current_cycle,
        "next_sequence": lot_setting.current_sequence + 1,
        "default_group_size": default_group_size,
    }

    return render(request, "factory/final_product_entry.html", context)