"""
دالة مشتركة لتحويل حرف مجموعة التدوير (A/B/C/D) + تاريخ معيّن
إلى نوع الوردية الفعلي (ShiftType) في ذلك اليوم، بالرجوع لدورة الـ 8 أيام
(ShiftRotationPattern) ويوم الصفر المرجعي (RotationReference).

تُستخدم من factory/views.py و factory/admin.py معًا لضمان نفس منطق
الحساب في كل مكان يُطلب فيه "الوردية" من مستخدم اختار مجموعة تدوير.
"""

from django.db import connection

from employees.models import ShiftGroup, ShiftType


def resolve_shift_type(group_letter, target_date):
    """
    group_letter: حرف المجموعة كما هو مخزّن في shift_groups.group_name (مثال: "A")
    target_date: كائن date (وليس datetime) يمثل تاريخ الإنتاج/السحب

    يرجّع كائن ShiftType، أو None لو الحرف/التاريخ غير صالحين أو لم يوجد
    صف مطابق في جدول الدورة.

    ملاحظة: نستخدم استعلامات مباشرة على الجداول legacy لأنها قد لا تحتوي
    عمود id، فلا يمكن الاعتماد على Django ORM الذي يفترض وجوده.
    """
    if not group_letter or not target_date:
        return None

    try:
        group = ShiftGroup.objects.filter(group_name=group_letter).first()
        if not group:
            return None

        with connection.cursor() as cursor:
            cursor.execute("SELECT reference_date FROM rotation_reference LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            reference_date = row[0]

            day_offset = (target_date - reference_date).days % 8

            cursor.execute(
                "SELECT shift_type_id FROM shift_rotation_pattern "
                "WHERE group_id = %s AND day_offset = %s",
                [group.group_id, day_offset],
            )
            row = cursor.fetchone()
            if not row:
                return None
            shift_type_id = row[0]
    except Exception:
        return None

    return ShiftType.objects.filter(shift_type_id=shift_type_id).first()