"""
وحدة عرض/تعديل البيانات السابقة (صفحة داتا).

تبني شبكة منسقة على نفس تقسيم صفحة الإدخال: عينة ممثلة + أطنانها،
مع عرض النتائج الكيميائية والفيزيائية وقرارات الجريد القابلة للتعديل.
لا توجد أي عملية إضافة جديدة — فقط عرض وتعديل البيانات الموجودة.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from .models import (
    Grade,
    GradeReason,
    RepresentativeSample,
    SampleChemicalResult,
    TestDefinition,
    Ton,
    TonGradeAssignment,
    TonPhysicalResult,
)
from .shift_resolver import resolve_shift_type


def _fmt_time(value):
    if not value:
        return ""
    return value.strftime("%H:%M")


def _fmt_date(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")


def _num(value):
    if value is None:
        return ""
    return str(value)


def build_reading_grid(reading):
    """
    يبني كل بيانات القراءة (عينة ممثلة + أطنان) على نفس تقسيم صفحة الإدخال.
    كل طن يمثل سطراً، والعينة الممثلة توفر القيم المشتركة والنتائج الكيميائية.
    """
    tons = list(
        reading.tons.all()
        .select_related("production_shift", "grade_assignment__primary_grade", "grade_assignment__secondary_grade", "grade_assignment__reason")
        .order_by("sequence_number", "id")
    )

    reps = RepresentativeSample.objects.filter(tons__in=tons).distinct() if tons else RepresentativeSample.objects.none()

    chemical_results = {}
    if tons:
        for cr in SampleChemicalResult.objects.filter(ton__in=tons).select_related("test"):
            chemical_results[(cr.ton_id, cr.test_id)] = cr.result

    physical_results = {}
    if tons:
        for pr in TonPhysicalResult.objects.filter(ton__in=tons).select_related("test"):
            physical_results[(pr.ton_id, pr.test_id)] = pr.result

    assignment_by_ton = {}
    for ton in tons:
        try:
            assignment_by_ton[ton.pk] = ton.grade_assignment
        except TonGradeAssignment.DoesNotExist:
            pass

    chemical_tests = TestDefinition.objects.filter(
        plant=reading.plant, category="chemical",
        scopes__contains=[TestDefinition.SCOPE_FINAL_PRODUCT],
    ).order_by("id")
    physical_tests = TestDefinition.objects.filter(
        plant=reading.plant, category="physical",
        scopes__contains=[TestDefinition.SCOPE_FINAL_PRODUCT],
    ).order_by("id")

    rep_for_ton = {}
    if reps:
        for rep in reps.prefetch_related("tons"):
            for t in rep.tons.all():
                rep_for_ton.setdefault(t.pk, rep)

    rep = reps[0] if reps else None

    rows = []
    for ton in tons:
        current_rep = rep_for_ton.get(ton.pk) or rep
        assignment = assignment_by_ton.get(ton.pk)
        rows.append({
            "ton": ton,
            "rep": current_rep,
            "weight": _num(ton.weight),
            "production_date": _fmt_date(ton.production_date),
            "shift": getattr(ton.production_shift, "name", "") if ton.production_shift else "",
            "packing_location": reading.packing_location.name if reading.packing_location else "",
            "sampling_time": _fmt_time(reading.sampled_at),
            "sampling_status": reading.sampling_status,
            "sampled_by": reading.sampled_by_id,
            "analyzed_by": reading.analyzed_by_id,
            "lab_shift_head": reading.lab_shift_head_id,
            "reviewed_by": reading.reviewed_by_id,
            "result_time": _fmt_time(reading.result_time),
            "primary_grade": assignment.primary_grade_id if assignment else None,
            "secondary_grade": assignment.secondary_grade_id if assignment else None,
            "local_reason": assignment.reason_id if assignment and assignment.reason and assignment.reason.reason_type == GradeReason.REASON_LOCAL else None,
            "non_conforming_reason": assignment.reason_id if assignment and assignment.reason and assignment.reason.reason_type == GradeReason.REASON_NON_CONFORMING else None,
            "chemical": {},
            "chemical_values": {t.id: _num(chemical_results.get((ton.pk, t.id))) for t in chemical_tests},
            "physical_values": {t.id: _num(physical_results.get((ton.pk, t.id))) for t in physical_tests},
        })

    return {
        "reading": reading,
        "rows": rows,
        "rep": rep,
        "chemical_tests": list(chemical_tests),
        "physical_tests": list(physical_tests),
        "primary_grades": list(Grade.objects.filter(plant=reading.plant, grade_type=Grade.TYPE_PRIMARY, is_active=True)),
        "secondary_grades": list(Grade.objects.filter(plant=reading.plant, grade_type=Grade.TYPE_SECONDARY, is_active=True)),
        "local_reasons": list(GradeReason.objects.filter(plant=reading.plant, reason_type=GradeReason.REASON_LOCAL)),
        "non_conforming_reasons": list(GradeReason.objects.filter(plant=reading.plant, reason_type=GradeReason.REASON_NON_CONFORMING)),
        "users": list(
            get_user_model().objects.filter(is_active=True).values("id", "first_name", "last_name", "username")
        ),
    }


@transaction.atomic
def save_reading_edits(plant, reading, rows, user):
    """
    يحفظ تعديلات شبكة القراءة الحالية. لا يُنشئ أطناناً جديدة ولا يحذف موجودة.
    يعدّل: قيم الأطنان، النتائج، الجريد، الأسباب، والحقول المشتركة للقراءة.
    """
    errors = []
    ton_rows = [r for r in rows if r.get("row_type") == "ton"]

    try:
        rep_sample = RepresentativeSample.objects.filter(tons__in=[r["ton_id"] for r in ton_rows]).distinct().first()
    except Exception:
        rep_sample = None

    # الحقول المشتركة من أول صف
    first = ton_rows[0] if ton_rows else {}
    production_date = parse_date(first.get("production_date")) if first.get("production_date") else timezone.localdate()
    shift_type_obj = None
    if first.get("shift"):
        try:
            shift_type_obj = resolve_shift_type(first.get("shift"), production_date)
        except Exception:
            shift_type_obj = None

    reading.packing_location_id = first.get("packing_location_id") or reading.packing_location_id
    reading.sampling_status = first.get("sampling_status", reading.sampling_status)
    reading.sampled_by_id = first.get("qc_inspector_id") or reading.sampled_by_id
    reading.analyzed_by_id = first.get("lab_chemist_id") or reading.analyzed_by_id
    reading.lab_shift_head_id = first.get("lab_shift_head_id") or reading.lab_shift_head_id
    if first.get("qc_shift_head") == "reviewed":
        reading.reviewed_by = user
    else:
        reading.reviewed_by = None
    reading.result_time = parse_time(first.get("result_time")) if first.get("result_time") else reading.result_time
    reading.save()

    for row in ton_rows:
        try:
            ton = Ton.objects.get(pk=row["ton_id"], plant=plant)
        except (Ton.DoesNotExist, KeyError, ValueError):
            errors.append(f"طن غير موجود: {row.get('ton_id')}")
            continue

        if row.get("production_date"):
            d = parse_date(row["production_date"])
            if d:
                ton.production_date = d
        if row.get("weight") not in (None, ""):
            try:
                ton.weight = Decimal(str(row["weight"]))
            except Exception:
                pass
        if shift_type_obj is not None:
            ton.production_shift = shift_type_obj
        ton.save()

        # النتائج الفيزيائية
        for test_id, val in (row.get("physical") or {}).items():
            try:
                test = TestDefinition.objects.get(pk=test_id)
                if val not in (None, ""):
                    TonPhysicalResult.objects.update_or_create(ton=ton, test=test, defaults={"result": Decimal(str(val))})
            except (TestDefinition.DoesNotExist, ValueError, Exception):
                pass

        # النتائج الكيميائية (مرتبطة بالعينة الممثلة)
        for test_id, val in (row.get("chemical") or {}).items():
            try:
                test = TestDefinition.objects.get(pk=test_id)
                if val in (None, ""):
                    continue
                SampleChemicalResult.objects.update_or_create(
                    ton=ton,
                    test=test,
                    defaults={
                        "representative_sample": rep_sample,
                        "result": Decimal(str(val)),
                        "is_overridden": True,
                    },
                )
            except (TestDefinition.DoesNotExist, ValueError, Exception):
                pass

        # قرار الجريد
        primary_id = row.get("primary_grade_id") or row.get("grade_id")
        reason_id = row.get("local_reason_id") or row.get("non_conforming_reason_id") or None
        if primary_id:
            primary = Grade.objects.filter(pk=primary_id, plant=plant).first()
            if primary:
                secondary = Grade.objects.filter(pk=row.get("secondary_grade_id"), plant=plant).first() if row.get("secondary_grade_id") else None
                TonGradeAssignment.objects.update_or_create(
                    ton=ton,
                    defaults={
                        "primary_grade": primary,
                        "secondary_grade": secondary,
                        "reason_id": reason_id,
                        "assigned_by": user,
                    },
                )
        else:
            TonGradeAssignment.objects.filter(ton=ton).delete()

        # تحديث حالة الطن حسب الجريد
        has_assignment = TonGradeAssignment.objects.filter(ton=ton).exists()
        if has_assignment:
            ton.status = Ton.STATUS_GRADED
            ton.save(update_fields=["status", "production_date", "production_shift", "weight"])

    return errors
