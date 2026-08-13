import json
from datetime import datetime, time as dt_time
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.dateparse import parse_date, parse_datetime
from django.contrib.auth import get_user_model

from plants.models import Plant
from .shift_resolver import resolve_shift_type
from .models import (
    ProcessStage,
    TestDefinition,
    ProcessReading,
    ProcessAnalysisResult,
    OutputPoint,
    OutputReading,
    Ton,
    RepresentativeSample,
    TonPhysicalResult,
    SampleChemicalResult,
    TonGradeAssignment,
    PlantLotSetting,
    RepresentativeGroupSize,
    GradeReason,
    PackingType,
    PackingLocation,
    Grade,
)

User = get_user_model()


@staff_member_required
def process_reading_grid(request):
    plant_id = request.GET.get("plant") or request.POST.get("plant")
    plant = Plant.objects.filter(pk=plant_id).first() if plant_id else None
    stages = ProcessStage.objects.filter(plant=plant) if plant else ProcessStage.objects.none()
    tests = TestDefinition.objects.filter(plant=plant, scope="process") if plant else TestDefinition.objects.none()

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
                        stage = ProcessStage.objects.filter(pk=stage_id).first() if stage_id else None
                        reading = ProcessReading.objects.create(
                            plant=plant,
                            stage=stage,
                            sampled_at=sampled_at
                        )
                        test_results = {**row.get("chemical", {}), **row.get("physical", {})}
                        for test_id, val_raw in test_results.items():
                            if val_raw != "" and val_raw is not None:
                                try:
                                    test_obj = TestDefinition.objects.get(pk=test_id)
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
        return redirect(f"{request.path}?plant={plant_id}")

    selected_stage_ids = [int(s) for s in request.GET.getlist("stages")]
    selected_stages = ProcessStage.objects.filter(plant=plant, pk__in=selected_stage_ids) if plant else ProcessStage.objects.none()

    context = {
        "plants": Plant.objects.all(),
        "plant": plant,
        "stages": stages,
        "tests": tests,
        "selected_stage_ids": selected_stage_ids,
        "selected_stages": selected_stages,
    }
    return render(request, "factory/process_reading_grid.html", context)


def _combine_datetime(date_str, time_str):
    if not date_str:
        return None
    d = parse_date(date_str)
    if not d:
        return None
    t = dt_time(0, 0)
    if time_str:
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            pass
    naive = datetime.combine(d, t)
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


def _get_or_create_output_point(plant, packing_location):
    if not packing_location:
        return None
    output_point, _ = OutputPoint.objects.get_or_create(
        plant=plant,
        code=f"PL{packing_location.id}",
        defaults={"name": packing_location.name},
    )
    return output_point


def _get_or_create_default_output_point(plant):
    output_point, _ = OutputPoint.objects.get_or_create(
        plant=plant, code="DEFAULT", defaults={"name": "نقطة سحب عامة"}
    )
    return output_point


def _save_rows(plant, packing_type, rows, request_user):
    ton_rows = [r for r in rows if r.get("row_type") == "ton"]
    rep_rows = {r.get("group"): r for r in rows if r.get("row_type") == "representative"}

    group_context = {}
    for group_letter, rep in rep_rows.items():
        packing_location = None
        if rep.get("packing_location_id"):
            packing_location = PackingLocation.objects.filter(pk=rep["packing_location_id"]).first()
        group_context[group_letter] = {
            "rep_sample": RepresentativeSample.objects.create(plant=plant, cycle_number=0),
            "packing_location": packing_location,
            "row": rep,
        }

    saved = 0

    for row in ton_rows:
        group_letter = row.get("group")
        source_row = group_context[group_letter]["row"] if group_letter in group_context else row

        try:
            weight = Decimal(str(row.get("weight"))) if row.get("weight") not in (None, "") else Decimal("0")
        except InvalidOperation:
            weight = Decimal("0")

        production_date = parse_date(row.get("production_date")) if row.get("production_date") else None
        effective_date = production_date or timezone.localdate()

        shift_type_obj = resolve_shift_type(source_row.get("shift"), effective_date)

        packing_location = None
        if row.get("packing_location_id"):
            packing_location = PackingLocation.objects.filter(pk=row["packing_location_id"]).first()
        elif group_letter and group_letter in group_context:
            packing_location = group_context[group_letter]["packing_location"]

        output_point = _get_or_create_output_point(plant, packing_location) or _get_or_create_default_output_point(plant)

        reading = OutputReading.objects.create(
            plant=plant,
            output_point=output_point,
            packing_location=packing_location,
            packing_type=packing_type,
            product_name=source_row.get("product_type", ""),
            sampled_at=_combine_datetime(source_row.get("production_date"), source_row.get("sampling_time")) or timezone.now(),
            shift=shift_type_obj,
            sampled_by_id=source_row.get("qc_inspector_id") or None,
            analyzed_by_id=source_row.get("lab_chemist_id") or None,
            lab_shift_head_id=source_row.get("lab_shift_head_id") or None,
            reviewed_by=request_user if source_row.get("qc_shift_head") == "reviewed" else None,
        )

        ton = Ton.objects.create(
            plant=plant,
            output_reading=reading,
            weight=weight,
            production_date=effective_date,
            production_shift=shift_type_obj,
        )

        if group_letter and group_letter in group_context:
            rep_sample = group_context[group_letter]["rep_sample"]
        else:
            rep_sample = RepresentativeSample.objects.create(plant=plant, cycle_number=ton.cycle_number)

        rep_sample.tons.add(ton)
        rep_sample.refresh_derived_fields()

        for test_id, val in row.get("physical", {}).items():
            try:
                test_obj = TestDefinition.objects.get(pk=test_id)
                TonPhysicalResult.objects.update_or_create(
                    ton=ton, test=test_obj, defaults={"result": Decimal(str(val))}
                )
            except (TestDefinition.DoesNotExist, InvalidOperation):
                continue

        for test_id, val in row.get("chemical", {}).items():
            try:
                test_obj = TestDefinition.objects.get(pk=test_id)
                result_value = Decimal(str(val))
            except (TestDefinition.DoesNotExist, InvalidOperation):
                continue
            SampleChemicalResult.objects.update_or_create(
                ton=ton,
                test=test_obj,
                defaults={
                    "representative_sample": rep_sample,
                    "result": result_value,
                    "is_overridden": not bool(group_letter),
                },
            )

        grade_id = row.get("grade_id")
        if grade_id:
            reason_id = row.get("local_reason_id") or row.get("non_conforming_reason_id") or None
            try:
                grade_obj = Grade.objects.get(pk=grade_id)
                TonGradeAssignment.objects.update_or_create(
                    ton=ton,
                    defaults={
                        "grade": grade_obj,
                        "assigned_by": request_user,
                        "reason_id": reason_id,
                    },
                )
            except Grade.DoesNotExist:
                pass

        saved += 1

    return saved


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
            with transaction.atomic():
                saved_count = _save_rows(plant, packing_type, rows, request.user)
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
        "next_cycle": lot_setting.current_cycle,
        "next_sequence": lot_setting.current_sequence + 1,
        "default_group_size": default_group_size,
    }

    return render(request, "factory/final_product_entry.html", context)