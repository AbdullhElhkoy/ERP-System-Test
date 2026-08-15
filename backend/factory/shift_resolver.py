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


def resolve_group_letter(shift_type, target_date):
    """
    عكس resolve_shift_type: يحوّل كائن ShiftType + تاريخ معيّن إلى حرف مجموعة
    التدوير (A/B/C/D) في ذلك اليوم، للعرض في صفحات البيانات.

    يرجّع "" لو لم يمكن تحديد الحرف.
    """
    if not shift_type or not target_date:
        return ""

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT reference_date FROM rotation_reference LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return ""
            reference_date = row[0]
            day_offset = (target_date - reference_date).days % 8

            cursor.execute(
                "SELECT g.group_name "
                "FROM shift_rotation_pattern p "
                "JOIN shift_groups g ON g.group_id = p.group_id "
                "WHERE p.day_offset = %s AND p.shift_type_id = %s "
                "ORDER BY g.group_name LIMIT 1",
                [day_offset, shift_type.shift_type_id],
            )
            row = cursor.fetchone()
            if not row:
                return ""
            return row[0] or ""
    except Exception:
        return ""