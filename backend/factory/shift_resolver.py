"""
دالة مشتركة لتحويل حرف مجموعة التدوير (A/B/C/D) + تاريخ معيّن
إلى نوع الوردية الفعلي (ShiftType) في ذلك اليوم، بالرجوع لدورة الـ 8 أيام
(ShiftRotationPattern) ويوم الصفر المرجعي (RotationReference).

تُستخدم من factory/views.py و factory/admin.py معًا لضمان نفس منطق
الحساب في كل مكان يُطلب فيه "الوردية" من مستخدم اختار مجموعة تدوير.
"""

from employees.models import ShiftGroup, ShiftRotationPattern, RotationReference


def resolve_shift_type(group_letter, target_date):
    """
    group_letter: حرف المجموعة كما هو مخزّن في shift_groups.group_name (مثال: "A")
    target_date: كائن date (وليس datetime) يمثل تاريخ الإنتاج/السحب

    يرجّع كائن ShiftType، أو None لو الحرف/التاريخ غير صالحين أو لم يوجد
    صف مطابق في جدول الدورة.
    """
    if not group_letter or not target_date:
        return None

    group = ShiftGroup.objects.filter(group_name=group_letter).first()
    if not group:
        return None

    reference = RotationReference.objects.first()
    if not reference or not reference.reference_date:
        return None

    day_offset = (target_date - reference.reference_date).days % 8

    pattern = ShiftRotationPattern.objects.filter(group=group, day_offset=day_offset).first()
    if not pattern:
        return None

    return pattern.shift_type