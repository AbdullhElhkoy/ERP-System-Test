"""
موديلات "المنتج النهائي" لتطبيق factory.

هذا الملف أُعيد بناؤه بالكامل من الصفر ليطابق الشكل الفعلي الموجود في قاعدة
البيانات (تم التحقق عبر information_schema.columns و information_schema
foreign key constraints على كل جدول من جداول factory_*). كل الجداول كانت
فارغة (0 صف) وقت إعادة البناء، فلا يوجد خطر فقدان بيانات.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from plants.models import Plant
from employees.models import ShiftType
from .shared import TestDefinition, PackingLocation, PackingType, ConformityRule, Grade


# ============================================================
# 1) إعدادات الترقيم لكل مصنع (كود الطن + الدورة/Cycle)
# ============================================================

class PlantLotSetting(models.Model):
    LOT_MODE_WEIGHT_BASED = "weight_based"
    LOT_MODE_MANUAL = "manual"
    LOT_MODE_CHOICES = [
        (LOT_MODE_WEIGHT_BASED, "تلقائي حسب الوزن التراكمي"),
        (LOT_MODE_MANUAL, "يدوي"),
    ]

    plant = models.OneToOneField(Plant, on_delete=models.CASCADE, related_name="factory_lot_setting")
    lot_mode = models.CharField(max_length=20, choices=LOT_MODE_CHOICES, default=LOT_MODE_WEIGHT_BASED)
    sampling_department = models.CharField(max_length=100, blank=True, default="")
    current_cycle = models.PositiveIntegerField(default=1)
    current_sequence = models.PositiveIntegerField(default=0)
    reset_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("10000"))
    cumulative_weight = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "factory_plant_lot_settings"

    def __str__(self):
        return f"{self.plant} - Cycle {self.current_cycle} / Seq {self.current_sequence}"


# ============================================================
# 2) نقاط السحب (Output Points) واختباراتها
# ============================================================

class OutputPoint(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_output_points")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "factory_output_points"
        unique_together = (("plant", "code"),)

    def __str__(self):
        return f"{self.code} - {self.name}" if self.name else self.code


class OutputPointTest(models.Model):
    output_point = models.ForeignKey(OutputPoint, on_delete=models.CASCADE, related_name="output_point_tests")
    test = models.ForeignKey(TestDefinition, on_delete=models.CASCADE, related_name="output_point_links")

    class Meta:
        db_table = "factory_output_point_tests"
        unique_together = (("output_point", "test"),)

    def __str__(self):
        return f"{self.output_point} - {self.test}"


# ============================================================
# 3) قراءة نقطة السحب (OutputReading) — سياق كل عملية سحب/تعبئة
# ============================================================

class OutputReading(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_output_readings")
    # NOT NULL في الداتابيز فعليًا - نقطة السحب مطلوبة دايمًا
    output_point = models.ForeignKey(OutputPoint, on_delete=models.PROTECT, related_name="readings")
    packing_location = models.ForeignKey(
        PackingLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings"
    )
    packing_type = models.ForeignKey(
        PackingType, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings"
    )
    # مؤكد من قيود الداتابيز: shift هو FK حقيقي على shift_types (نفس جدول نظام الورديات)
    shift = models.ForeignKey(
        ShiftType, on_delete=models.SET_NULL, null=True, blank=True,
        db_column="shift_id", related_name="factory_output_readings",
    )
    product_name = models.CharField(max_length=100, blank=True, default="")
    sampled_at = models.DateTimeField()

    # عمود مخزّن فعليًا - يُملأ تلقائيًا من كود الطن (S-<ton_code>) في services.py
    sample_code = models.CharField(max_length=100, blank=True, default="")

    sampling_status = models.CharField(
        max_length=20, blank=True, default="",
        choices=[
            ("تم", "تم"),
            ("لم يتم", "لم يتم"),
        ],
        help_text="حالة سحب العينة من شاشة الإدخال",
    )
    result_time = models.TimeField(
        null=True, blank=True, help_text="وقت ظهور النتيجة"
    )

    notes = models.TextField(blank=True, default="")

    dynamic_data = models.JSONField(blank=True, default=dict, help_text="قيم الحقول الديناميكية المفعّلة لنوع التعبئة")

    sampled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_readings_sampled",
    )
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_readings_analyzed",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_readings_reviewed",
    )
    lab_shift_head = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_readings_lab_shift_head",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_output_readings"
        ordering = ["-sampled_at"]

    def __str__(self):
        return f"{self.plant} - {self.sampled_at:%Y-%m-%d %H:%M}"


class OutputAnalysisResult(models.Model):
    reading = models.ForeignKey(OutputReading, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="output_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_output_analysis_results"
        unique_together = (("reading", "test"),)

    def __str__(self):
        return f"{self.reading} - {self.test}: {self.result}"


# ============================================================
# 4) الطن (Ton) — الوحدة الأساسية للتتبع، مع الترقيم الذري
# ============================================================

class Ton(models.Model):
    STATUS_UNDER_TEST = "under_test"
    STATUS_SAMPLED = "sampled"
    STATUS_GRADED = "graded"
    STATUS_CHOICES = [
        (STATUS_UNDER_TEST, "تحت الاختبار (لم يُسحب)"),
        (STATUS_SAMPLED, "تم سحب العينة"),
        (STATUS_GRADED, "أخذ الجريد"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_tons")
    output_reading = models.ForeignKey(
        OutputReading, on_delete=models.CASCADE, related_name="tons", null=True, blank=True
    )
    weight = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0"))
    production_date = models.DateField()
    production_shift = models.ForeignKey(
        ShiftType, on_delete=models.SET_NULL, null=True, blank=True,
        db_column="production_shift_id", related_name="factory_tons",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_UNDER_TEST,
        help_text="حالة الطن: تحت الاختبار حتى تُسحب العينة وتظهر النتيجة",
    )

    code = models.CharField(max_length=30, blank=True, default="")
    cycle_number = models.PositiveIntegerField(default=0)
    sequence_number = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_tons"
        unique_together = (("plant", "code"),)
        ordering = ["-created_at"]

    def __str__(self):
        return self.code or f"Ton #{self.pk}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if creating and not self.code:
            with transaction.atomic():
                lot_setting, _ = PlantLotSetting.objects.select_for_update().get_or_create(plant=self.plant)

                lot_setting.current_sequence += 1
                lot_setting.cumulative_weight += self.weight or Decimal("0")

                if lot_setting.lot_mode == PlantLotSetting.LOT_MODE_WEIGHT_BASED:
                    threshold_crossed = (
                        lot_setting.reset_threshold > 0
                        and lot_setting.cumulative_weight > lot_setting.reset_threshold * lot_setting.current_cycle
                    )
                    if threshold_crossed:
                        lot_setting.current_cycle += 1

                lot_setting.save(update_fields=["current_sequence", "cumulative_weight", "current_cycle"])

                self.sequence_number = lot_setting.current_sequence
                self.cycle_number = lot_setting.current_cycle
                self.code = f"C{self.cycle_number}({self.sequence_number})"

        super().save(*args, **kwargs)


class TonPhysicalResult(models.Model):
    ton = models.ForeignKey(Ton, on_delete=models.CASCADE, related_name="physical_results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="ton_physical_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_ton_physical_results"
        unique_together = (("ton", "test"),)

    def __str__(self):
        return f"{self.ton} - {self.test}: {self.result}"


# ============================================================
# 5) العينة الممثلة (RepresentativeSample)
# ============================================================

class RepresentativeSample(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_representative_samples")
    cycle_number = models.PositiveIntegerField(default=0)
    code = models.CharField(max_length=40, blank=True, default="")
    weight = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0"))
    tons = models.ManyToManyField(Ton, related_name="representative_samples", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_representative_samples"
        ordering = ["-created_at"]

    def __str__(self):
        return self.code or f"RepSample #{self.pk}"

    def refresh_derived_fields(self):
        tons = list(self.tons.all().order_by("sequence_number"))
        self.weight = sum((t.weight for t in tons), Decimal("0"))
        if tons:
            self.cycle_number = tons[0].cycle_number
            seq_part = "+".join(str(t.sequence_number) for t in tons)
            self.code = f"C{self.cycle_number}({seq_part})"
        else:
            self.code = f"C{self.cycle_number}()"
        self.save(update_fields=["weight", "cycle_number", "code"])

    def apply_chemical_result(self, test, result, user=None):
        for ton in self.tons.all():
            SampleChemicalResult.objects.update_or_create(
                ton=ton,
                test=test,
                defaults={
                    "representative_sample": self,
                    "result": result,
                    "is_overridden": False,
                },
            )


class SampleChemicalResult(models.Model):
    ton = models.ForeignKey(Ton, on_delete=models.CASCADE, related_name="chemical_results")
    representative_sample = models.ForeignKey(
        RepresentativeSample, on_delete=models.SET_NULL, null=True, blank=True, related_name="chemical_results"
    )
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="sample_chemical_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    is_overridden = models.BooleanField(default=False)

    class Meta:
        db_table = "factory_sample_chemical_results"
        unique_together = (("ton", "test"),)

    def __str__(self):
        return f"{self.ton} - {self.test}: {self.result}"


# ============================================================
# 6) قرار الجريد (التصنيف) لكل طن
# ============================================================

class GradeReason(models.Model):
    REASON_LOCAL = "local"
    REASON_NON_CONFORMING = "non_conforming"
    REASON_TYPE_CHOICES = [
        (REASON_LOCAL, "محلي"),
        (REASON_NON_CONFORMING, "غير مطابق"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_grade_reasons")
    text = models.CharField(max_length=255)
    reason_type = models.CharField(max_length=20, choices=REASON_TYPE_CHOICES)

    class Meta:
        db_table = "factory_grade_reasons"

    def __str__(self):
        return self.text


class TonGradeAssignment(models.Model):
    ton = models.OneToOneField(Ton, on_delete=models.CASCADE, related_name="grade_assignment")
    primary_grade = models.ForeignKey(
        Grade, on_delete=models.PROTECT, related_name="ton_primary_assignments",
        help_text="الجريد الأساسي (تصدير / محلي / غير مطابق)",
    )
    secondary_grade = models.ForeignKey(
        Grade, on_delete=models.SET_NULL, null=True, blank=True, related_name="ton_secondary_assignments",
        help_text="الجريد الثانوي التابع للأساسي (اختياري)",
    )
    reason = models.ForeignKey(
        GradeReason, on_delete=models.SET_NULL, null=True, blank=True, related_name="ton_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="grade_assignments"
    )
    assigned_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "factory_ton_grade_assignments"

    def __str__(self):
        if self.secondary_grade_id:
            return f"{self.ton} -> {self.primary_grade} / {self.secondary_grade}"
        return f"{self.ton} -> {self.primary_grade}"


# ============================================================
# 7) حجم مجموعة العينة الممثلة الافتراضي
# ============================================================

class RepresentativeGroupSize(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_group_sizes")
    packing_type = models.ForeignKey(PackingType, on_delete=models.CASCADE, related_name="group_sizes")
    default_group_size = models.PositiveSmallIntegerField(default=4)

    class Meta:
        db_table = "factory_representative_group_sizes"
        unique_together = (("plant", "packing_type"),)

    def __str__(self):
        return f"{self.plant} - {self.packing_type}: {self.default_group_size}"


# ============================================================
# 8) التعبئة والتحويل (Packing)
# ============================================================

class PackingEvent(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_events")
    output_reading = models.ForeignKey(
        OutputReading, on_delete=models.CASCADE, related_name="packing_events"
    )
    packing_type = models.ForeignKey(PackingType, on_delete=models.PROTECT, related_name="packing_events")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default="بيج باج")
    packed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_packing_events"
        ordering = ["-packed_at"]

    def __str__(self):
        return f"{self.output_reading} - {self.quantity} {self.unit}"


class PackingConversion(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_conversions")
    source_event = models.ForeignKey(PackingEvent, on_delete=models.CASCADE, related_name="conversions_out")
    target_packing_type = models.ForeignKey(PackingType, on_delete=models.PROTECT, related_name="conversions_in")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default="شكارة")
    converted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "factory_packing_conversions"
        ordering = ["-converted_at"]

    def __str__(self):
        return f"{self.source_event} -> {self.target_packing_type}: {self.quantity} {self.unit}"


class QualityConformityResult(models.Model):
    reading = models.ForeignKey(OutputReading, on_delete=models.CASCADE, related_name="conformity_results")
    conformity_rule = models.ForeignKey(ConformityRule, on_delete=models.PROTECT, related_name="results")
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True, related_name="conformity_results")
    quality_grade = models.ForeignKey(
        "shared_definitions.QualityGrade", on_delete=models.PROTECT, related_name="conformity_results"
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "factory_quality_conformity_results"

    def __str__(self):
        return f"{self.reading} - {self.conformity_rule}"


# ============================================================
# 9) المخزون الأرضي (Floor Stock) — موجود بالداتابيز، لم يكن موثقًا سابقًا
# ============================================================

class FloorStockBalance(models.Model):
    """
    رصيد المخزون الأرضي الحالي لكل (مصنع + جريد + حالة).
    سطر واحد لكل توليفة. القسمان المنتظران للجريد لا يحملان جريداً (grade=None).
    """
    STATUS_GRADED = "graded"
    STATUS_WAITING_NOT_SAMPLED = "waiting_not_sampled"
    STATUS_WAITING_SAMPLED = "waiting_sampled"
    STATUS_CHOICES = [
        (STATUS_GRADED, "أخذ الجريد"),
        (STATUS_WAITING_NOT_SAMPLED, "في انتظار الجريد (لم يُسحب للمعمل)"),
        (STATUS_WAITING_SAMPLED, "في انتظار الجريد (تم السحب للمعمل)"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_floor_stock_balances")
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="floor_stock_balances",
        help_text="الجريد فقط لقسم \"أخذ الجريد\"، يبقى فارغاً للأقسام المنتظرة",
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_GRADED)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "factory_floor_stock_balances"
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "grade", "status"],
                condition=models.Q(status="graded"),
                name="uniq_floorstock_plant_grade_graded",
            ),
            models.UniqueConstraint(
                fields=["plant", "status"],
                condition=models.Q(status__in=["waiting_not_sampled", "waiting_sampled"]),
                name="uniq_floorstock_plant_waiting_status",
            ),
        ]

    def __str__(self):
        grade_label = f" - {self.grade}" if self.grade_id else ""
        return f"{self.plant}{grade_label} [{self.get_status_display()}]: {self.quantity}"


class FloorStockMovement(models.Model):
    """
    سجل حركات المخزون الأرضي (إضافة/سحب) لكل (مصنع + جريد + حالة)، مع ربط اختياري
    بالطن المصدر.
    """
    MOVEMENT_IN = "in"
    MOVEMENT_OUT = "out"
    MOVEMENT_TYPE_CHOICES = [
        (MOVEMENT_IN, "إضافة"),
        (MOVEMENT_OUT, "سحب"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_floor_stock_movements")
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="floor_stock_movements"
    )
    status = models.CharField(
        max_length=30, choices=FloorStockBalance.STATUS_CHOICES, default=FloorStockBalance.STATUS_GRADED
    )
    ton = models.ForeignKey(
        Ton, on_delete=models.SET_NULL, null=True, blank=True, related_name="floor_stock_movements"
    )
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    occurred_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "factory_floor_stock_movements"
        ordering = ["-occurred_at"]

    def __str__(self):
        grade_label = f" - {self.grade}" if self.grade_id else ""
        return f"{self.plant}{grade_label} [{self.get_status_display()}]: {self.movement_type} {self.quantity}"
