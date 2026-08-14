"""
طبقة الخدمات الموحّدة لتطبيق factory.

كل منطق حفظ البيانات يُنفَّذ هنا في مكان واحد، بدلاً من تكراره في
factory/views.py و factory/admin.py. أي شاشة أو API أو تطبيق خارجي
يستدعي هذه الدوال للحفظ بنفس الطريقة تماماً.
"""

from datetime import datetime, time as dt_time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from .models import (
    OutputPoint,
    OutputReading,
    PackingLocation,
    Grade,
    RepresentativeSample,
    SampleChemicalResult,
    TestDefinition,
    Ton,
    TonGradeAssignment,
    TonPhysicalResult,
)
from .shift_resolver import resolve_shift_type


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
        code=f"PL{packing_location.pk}",
        defaults={"name": packing_location.name},
    )
    return output_point


def _get_or_create_default_output_point(plant):
    output_point, _ = OutputPoint.objects.get_or_create(
        plant=plant, code="DEFAULT", defaults={"name": "نقطة سحب عامة"}
    )
    return output_point


def _as_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _resolve_test(test_id):
    if not test_id:
        return None
    try:
        return TestDefinition.objects.get(pk=test_id)
    except (TestDefinition.DoesNotExist, ValueError):
        return None


def _apply_grade(ton, row, user):
    grade_id = row.get("grade_id")
    if not grade_id:
        return
    grade = Grade.objects.filter(pk=grade_id).first()
    if not grade:
        return
    reason_id = row.get("local_reason_id") or row.get("non_conforming_reason_id") or None
    TonGradeAssignment.objects.update_or_create(
        ton=ton,
        defaults={
            "grade": grade,
            "reason_id": reason_id,
            "assigned_by": user,
        },
    )


def _apply_ton_physical_results(ton, row):
    for test_id, val in (row.get("physical") or {}).items():
        test = _resolve_test(test_id)
        result = _as_decimal(val)
        if test and result is not None:
            TonPhysicalResult.objects.update_or_create(
                ton=ton, test=test, defaults={"result": result}
            )


def _apply_solo_chemical_results(ton, rep_sample, row):
    for test_id, val in (row.get("chemical") or {}).items():
        test = _resolve_test(test_id)
        result = _as_decimal(val)
        if test and result is not None:
            SampleChemicalResult.objects.update_or_create(
                ton=ton,
                test=test,
                defaults={
                    "representative_sample": rep_sample,
                    "result": result,
                    "is_overridden": False,
                },
            )


@transaction.atomic
def save_final_product_rows(plant, packing_type, rows, user):
    """
    الحفظ الموحّد لشاشة إدخال المنتج النهائي.

    rows: قائمة صفوف (ton / representative) كما يرسلها القالب أو أي عميل.
    يرجّع عدد الأطنان المحفوظة.
    """
    ton_rows = [r for r in rows if r.get("row_type") == "ton"]
    rep_rows = {r.get("group"): r for r in rows if r.get("row_type") == "representative"}

    tons_by_group = {}
    saved = 0

    for row in ton_rows:
        group_letter = row.get("group")
        rep_row = rep_rows.get(group_letter, {}) if group_letter else None
        source = rep_row or row

        production_date = parse_date(row.get("production_date")) or timezone.localdate()
        shift_type_obj = resolve_shift_type(source.get("shift"), production_date)

        packing_location = None
        if row.get("packing_location_id"):
            packing_location = PackingLocation.objects.filter(pk=row["packing_location_id"]).first()
        elif source.get("packing_location_id"):
            packing_location = PackingLocation.objects.filter(pk=source["packing_location_id"]).first()

        output_point = (
            _get_or_create_output_point(plant, packing_location)
            or _get_or_create_default_output_point(plant)
        )

        reading = OutputReading.objects.create(
            plant=plant,
            output_point=output_point,
            packing_location=packing_location,
            packing_type=packing_type,
            product_name=source.get("product_type", "") or (packing_type.name if packing_type else ""),
            sampled_at=_combine_datetime(
                source.get("production_date"), source.get("sampling_time")
            ) or timezone.now(),
            shift=shift_type_obj,
            sampling_status=row.get("sampling_status", ""),
            result_time=parse_time(row.get("result_time")) if row.get("result_time") else None,
            sampled_by_id=source.get("qc_inspector_id") or None,
            analyzed_by_id=source.get("lab_chemist_id") or None,
            lab_shift_head_id=source.get("lab_shift_head_id") or None,
            reviewed_by=user if source.get("qc_shift_head") == "reviewed" else None,
        )

        ton = Ton.objects.create(
            plant=plant,
            output_reading=reading,
            weight=_as_decimal(row.get("weight")) or Decimal("0"),
            production_date=production_date,
            production_shift=shift_type_obj,
        )

        reading.sample_code = f"S-{ton.code}"
        reading.save(update_fields=["sample_code"])

        _apply_ton_physical_results(ton, row)
        _apply_grade(ton, row, user)

        if group_letter:
            tons_by_group.setdefault(group_letter, []).append(ton)
        else:
            solo_rep = RepresentativeSample.objects.create(
                plant=plant, cycle_number=ton.cycle_number
            )
            solo_rep.tons.add(ton)
            solo_rep.refresh_derived_fields()
            _apply_solo_chemical_results(ton, solo_rep, row)

        saved += 1

    # العينات الممثلة: عينة واحدة، ونتائجها الكيميائية تتوزع على كل الأطنان
    for group_letter, tons in tons_by_group.items():
        rep_row = rep_rows.get(group_letter, {})
        rep = RepresentativeSample.objects.create(
            plant=plant,
            cycle_number=tons[0].cycle_number if tons else 1,
        )
        rep.tons.set(tons)
        rep.refresh_derived_fields()

        for test_id, val in (rep_row.get("chemical") or {}).items():
            test = _resolve_test(test_id)
            result = _as_decimal(val)
            if test and result is not None:
                rep.apply_chemical_result(test=test, result=result, user=user)

        lab_chemist_id = rep_row.get("lab_chemist_id") or None
        lab_shift_head_id = rep_row.get("lab_shift_head_id") or None
        qc_status = rep_row.get("qc_shift_head") or None

        for ton in tons:
            if not ton.output_reading:
                continue
            update_fields = []
            if lab_chemist_id and not ton.output_reading.analyzed_by_id:
                ton.output_reading.analyzed_by_id = lab_chemist_id
                update_fields.append("analyzed_by_id")
            if lab_shift_head_id and not ton.output_reading.lab_shift_head_id:
                ton.output_reading.lab_shift_head_id = lab_shift_head_id
                update_fields.append("lab_shift_head_id")
            if qc_status == "reviewed":
                ton.output_reading.reviewed_by = user
                update_fields.append("reviewed_by")
            if update_fields:
                ton.output_reading.save(update_fields=update_fields)

    return saved
