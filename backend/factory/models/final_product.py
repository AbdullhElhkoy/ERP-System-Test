from django.conf import settings
from django.db import models, transaction
from plants.models import Plant
from shared_definitions.models import QualityGrade
from .shared import TestDefinition, PackingLocation, PackingType, ConformityRule, Grade


class OutputPoint(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_output_points")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "factory_output_points"
        unique_together = (("plant", "code"),)

    def __str__(self):
        return f"{self.code} - {self.name}"


class OutputPointTest(models.Model):
    output_point = models.ForeignKey(OutputPoint, on_delete=models.CASCADE, related_name="point_tests")
    test = models.ForeignKey(TestDefinition, on_delete=models.CASCADE, related_name="output_point_links")

    class Meta:
        db_table = "factory_output_point_tests"
        unique_together = (("output_point", "test"),)

    def __str__(self):
        return f"{self.output_point} - {self.test}"


class OutputReading(models.Model):
    """
    سحب العينة - أول حدث بيتسجل فعلياً في المرحلة دي.
    """
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_output_readings")
    output_point = models.ForeignKey(OutputPoint, on_delete=models.PROTECT, related_name="readings")

    product_name = models.CharField(max_length=100, blank=True)
    sampled_at = models.DateTimeField()
    shift = models.ForeignKey(
        "employees.ShiftType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_output_readings",
        help_text="بتتحدد تلقائيًا من الوردية الثابتة بتاعة المستخدم، والأدمن يقدر يعدّلها وقت الحاجة"
    )
    packing_location = models.ForeignKey(PackingLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings")
    packing_type = models.ForeignKey(PackingType, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings")

    sampled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples_taken"
    )
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples_analyzed"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples_reviewed",
        help_text="ممكن يتحدد بعدين لما التحليل يخلص، مش لازم وقت السحب"
    )

    sample_code = models.CharField(max_length=50, blank=True, editable=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_output_readings"
        ordering = ["-sampled_at"]

    def __str__(self):
        return self.sample_code or f"{self.output_point} - {self.sampled_at:%Y-%m-%d %H:%M}"


class OutputAnalysisResult(models.Model):
    reading = models.ForeignKey(OutputReading, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="output_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_output_analysis_results"
        unique_together = (("reading", "test"),)

    def __str__(self):
        return f"{self.reading} - {self.test}: {self.result}"


class QualityConformityResult(models.Model):
    reading = models.OneToOneField(OutputReading, on_delete=models.CASCADE, related_name="conformity")
    conformity_rule = models.ForeignKey(ConformityRule, on_delete=models.PROTECT, related_name="results")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, null=True, blank=True, related_name="conformity_results")
    quality_grade = models.ForeignKey(QualityGrade, on_delete=models.PROTECT, related_name="conformity_results")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "factory_quality_conformity_results"

    def save(self, *args, **kwargs):
        if self.grade_id:
            self.quality_grade = self.grade.classification
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reading} -> {self.grade or self.quality_grade}"


class PackingEvent(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_events")
    output_reading = models.ForeignKey(OutputReading, on_delete=models.PROTECT, related_name="packing_events")
    packing_type = models.ForeignKey(PackingType, on_delete=models.PROTECT, related_name="packing_events")
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20, default="tons")
    packed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_packing_events"
        ordering = ["-packed_at"]

    def __str__(self):
        return f"{self.packing_type} - {self.quantity}{self.unit} - {self.packed_at:%Y-%m-%d %H:%M}"


class PackingConversion(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_conversions")
    source_event = models.ForeignKey(PackingEvent, on_delete=models.PROTECT, related_name="conversions_out")
    target_packing_type = models.ForeignKey(PackingType, on_delete=models.PROTECT, related_name="conversions_in")
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20, default="tons")
    converted_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_packing_conversions"
        ordering = ["-converted_at"]

    def __str__(self):
        return f"{self.source_event} -> {self.target_packing_type} ({self.quantity}{self.unit})"


class PlantLotSetting(models.Model):
    LOT_MODE_AUTO = "auto"
    LOT_MODE_MANUAL = "manual"
    LOT_MODE_CHOICES = [
        (LOT_MODE_AUTO, "توليد أوتوماتيكي"),
        (LOT_MODE_MANUAL, "إدخال يدوي من إدارة محددة"),
    ]

    plant = models.OneToOneField(Plant, on_delete=models.CASCADE, related_name="lot_setting")
    lot_mode = models.CharField(max_length=10, choices=LOT_MODE_CHOICES, default=LOT_MODE_AUTO)
    sampling_department = models.ForeignKey(
        "plants.Department", on_delete=models.PROTECT, null=True, blank=True,
        related_name="lot_sampling_plants",
        help_text="الإدارة المسؤولة عن سحب العينات لهذا المصنع"
    )
    reset_threshold = models.IntegerField(default=9999)
    current_cycle = models.IntegerField(default=1)
    current_sequence = models.IntegerField(default=0)

    class Meta:
        db_table = "factory_plant_lot_settings"

    def __str__(self):
        return f"{self.plant.plant_code} - C{self.current_cycle}"

    @transaction.atomic
    def next_sequence(self):
        setting = PlantLotSetting.objects.select_for_update().get(pk=self.pk)
        next_seq = setting.current_sequence + 1
        if next_seq > setting.reset_threshold:
            setting.current_cycle += 1
            next_seq = 1
        setting.current_sequence = next_seq
        setting.save(update_fields=["current_cycle", "current_sequence"])
        return setting.current_cycle, setting.current_sequence


class Ton(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="tons")
    output_reading = models.ForeignKey(
        OutputReading, on_delete=models.PROTECT, null=True, blank=True, related_name="tons",
        help_text="العينة اللي الطن ده جزء منها"
    )
    cycle_number = models.IntegerField()
    sequence_number = models.IntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=3)
    code = models.CharField(max_length=50, blank=True)
    production_date = models.DateField()
    production_shift = models.ForeignKey(
        "employees.ShiftType", on_delete=models.SET_NULL, null=True, blank=True, related_name="tons"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_tons"
        unique_together = (("plant", "cycle_number", "sequence_number"),)

    def save(self, *args, **kwargs):
        if not self.pk and (self.cycle_number is None or self.sequence_number is None):
            setting, _ = PlantLotSetting.objects.get_or_create(plant=self.plant)
            self.cycle_number, self.sequence_number = setting.next_sequence()
        if not self.code:
            self.code = f"C{self.cycle_number}({self.sequence_number})"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class RepresentativeSample(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="representative_samples")
    cycle_number = models.IntegerField()
    code = models.CharField(max_length=150, blank=True)
    tons = models.ManyToManyField(Ton, related_name="representative_samples")
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_representative_samples"

    def refresh_derived_fields(self):
        ton_list = list(self.tons.order_by("sequence_number"))
        if not ton_list:
            return
        self.weight = sum(t.weight for t in ton_list)
        if len(ton_list) == 1:
            self.code = ton_list[0].code
        else:
            joined = "+".join(str(t.sequence_number) for t in ton_list)
            self.code = f"C{self.cycle_number}({joined})"
        self.save(update_fields=["weight", "code"])

    def apply_chemical_result(self, test, result, user=None):
        """
        بتتسجل مرة واحدة على العينة، وتتوزع تلقائي على كل الأطنان المكوّنة ليها
        (غير اللي عندهم استثناء is_overridden=True بالفعل)
        """
        for ton in self.tons.all():
            existing = SampleChemicalResult.objects.filter(ton=ton, test=test).first()
            if existing and existing.is_overridden:
                continue
            SampleChemicalResult.objects.update_or_create(
                ton=ton, test=test,
                defaults={"representative_sample": self, "result": result, "is_overridden": False},
            )

    def __str__(self):
        return self.code


class TonPhysicalResult(models.Model):
    ton = models.ForeignKey(Ton, on_delete=models.CASCADE, related_name="physical_results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="ton_physical_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_ton_physical_results"
        unique_together = (("ton", "test"),)

    def __str__(self):
        return f"{self.ton.code} - {self.test}: {self.result}"


class SampleChemicalResult(models.Model):
    representative_sample = models.ForeignKey(RepresentativeSample, on_delete=models.CASCADE, related_name="chemical_results")
    ton = models.ForeignKey(Ton, on_delete=models.CASCADE, related_name="chemical_results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="sample_chemical_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    is_overridden = models.BooleanField(default=False)

    class Meta:
        db_table = "factory_sample_chemical_results"
        unique_together = (("ton", "test"),)

    def __str__(self):
        flag = " (معدّل)" if self.is_overridden else ""
        return f"{self.ton.code} - {self.test}: {self.result}{flag}"


class TonGradeAssignment(models.Model):
    """
    قرار الجريد النهائي لكل طن - وبمجرد ما يتحدد، الكمية بتتضاف تلقائي لرصيد الأرضية
    """
    ton = models.OneToOneField(Ton, on_delete=models.CASCADE, related_name="grade_assignment")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="ton_assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ton_grade_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "factory_ton_grade_assignments"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            FloorStockMovement.objects.create(
                plant=self.ton.plant, grade=self.grade,
                movement_type=FloorStockMovement.MOVEMENT_IN_PRODUCTION,
                quantity=self.ton.weight, ton=self.ton,
            )
            FloorStockBalance.adjust(self.ton.plant, self.grade, self.ton.weight)

    def __str__(self):
        return f"{self.ton.code} → {self.grade}"


class FloorStockBalance(models.Model):
    """
    الرصيد الحالي للمنتج النهائي في المصنع - لكل جريد لوحده، لحد وقت التسليم للمخزن
    """
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="floor_stock_balances")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="floor_stock_balances")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "factory_floor_stock_balances"
        unique_together = (("plant", "grade"),)

    def __str__(self):
        return f"{self.plant.plant_code} - {self.grade}: {self.quantity}"

    @classmethod
    @transaction.atomic
    def adjust(cls, plant, grade, delta):
        balance, _ = cls.objects.select_for_update().get_or_create(plant=plant, grade=grade)
        balance.quantity += delta
        balance.save(update_fields=["quantity", "updated_at"])
        return balance


class FloorStockMovement(models.Model):
    """سجل كل حركة زيادة/نقصان على رصيد الأرضية - للتتبع الكامل"""
    MOVEMENT_IN_PRODUCTION = "in_production"
    MOVEMENT_OUT_HANDOVER = "out_handover"
    MOVEMENT_TYPE_CHOICES = [
        (MOVEMENT_IN_PRODUCTION, "دخول - إنتاج"),
        (MOVEMENT_OUT_HANDOVER, "خروج - تسليم للمخزن"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="floor_stock_movements")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="floor_stock_movements")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    ton = models.ForeignKey(Ton, on_delete=models.PROTECT, null=True, blank=True, related_name="floor_stock_movements")
    occurred_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "factory_floor_stock_movements"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.plant.plant_code} - {self.get_movement_type_display()} - {self.grade}: {self.quantity}"