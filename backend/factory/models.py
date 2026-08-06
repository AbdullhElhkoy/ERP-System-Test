from django.conf import settings
from django.db import models, transaction
from plants.models import Plant
from shared_definitions.models import QualityGrade


# ═══════════ Definition Stages (تعريفات عامة للمصنع) ═══════════

class TestDefinition(models.Model):
    CATEGORY_CHEMICAL = "chemical"
    CATEGORY_PHYSICAL = "physical"
    CATEGORY_CHOICES = [
        (CATEGORY_CHEMICAL, "كيميائي"),
        (CATEGORY_PHYSICAL, "فيزيائي"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_test_definitions")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "factory_test_definitions"
        unique_together = (("plant", "name"),)

    def __str__(self):
        return f"{self.name} ({self.unit})" if self.unit else self.name


class PackingLocation(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_locations")
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "factory_packing_locations"
        unique_together = (("plant", "name"),)

    def __str__(self):
        return self.name


class PackingType(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_packing_types")
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "factory_packing_types"
        unique_together = (("plant", "name"),)

    def __str__(self):
        return self.name


class ConformityRule(models.Model):
    """
    قاعدة المصنع الخاصة اللي بتحوّل نتيجة فحص لواحدة من الـ 3 درجات المشتركة
    """
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_conformity_rules")
    name = models.CharField(max_length=100)
    quality_grade = models.ForeignKey(QualityGrade, on_delete=models.PROTECT, related_name="conformity_rules")
    description = models.TextField(blank=True)

    class Meta:
        db_table = "factory_conformity_rules"
        unique_together = (("plant", "name"),)

    def __str__(self):
        return f"{self.name} -> {self.quality_grade}"


class Grade(models.Model):
    """
    الجريد الفعلي بتاع كل مصنع (A, B, C... أو أي اسم يختاره الأدمن)
    مربوط بواحد من الـ 3 تصنيفات الثابتة في النظام
    """
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_grades")
    code = models.CharField(max_length=20)
    classification = models.ForeignKey(
        QualityGrade, on_delete=models.PROTECT, related_name="grades"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "factory_grades"
        unique_together = (("plant", "code"),)

    def __str__(self):
        return f"{self.code} ({self.classification})"


# ═══════════ Reaction ═══════════

class ProcessStage(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_process_stages")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "factory_process_stages"
        unique_together = (("plant", "code"),)

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProcessStageTest(models.Model):
    stage = models.ForeignKey(ProcessStage, on_delete=models.CASCADE, related_name="stage_tests")
    test = models.ForeignKey(TestDefinition, on_delete=models.CASCADE, related_name="process_stage_links")

    class Meta:
        db_table = "factory_process_stage_tests"
        unique_together = (("stage", "test"),)

    def __str__(self):
        return f"{self.stage} - {self.test}"


class ProcessReading(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_process_readings")
    stage = models.ForeignKey(ProcessStage, on_delete=models.PROTECT, related_name="readings")
    sampled_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_process_readings"
        ordering = ["-sampled_at"]

    def __str__(self):
        return f"{self.stage} - {self.sampled_at:%Y-%m-%d %H:%M}"


class ProcessAnalysisResult(models.Model):
    reading = models.ForeignKey(ProcessReading, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="process_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_process_analysis_results"
        unique_together = (("reading", "test"),)

    def __str__(self):
        return f"{self.reading} - {self.test}: {self.result}"


# ═══════════ Final Product ═══════════

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
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_output_readings")
    output_point = models.ForeignKey(OutputPoint, on_delete=models.PROTECT, related_name="readings")

    sampled_at = models.DateTimeField()
    shift = models.ForeignKey(
        "employees.ShiftType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="factory_output_readings",
        help_text="بتتحدد تلقائيًا من الوردية الثابتة بتاعة المستخدم، والأدمن يقدر يعدّلها وقت الحاجة"
    )
    packing_location = models.ForeignKey(PackingLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings")
    packing_type = models.ForeignKey(PackingType, on_delete=models.SET_NULL, null=True, blank=True, related_name="readings")

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
    grade = models.ForeignKey(
        Grade, on_delete=models.PROTECT, null=True, blank=True, related_name="conformity_results"
    )
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
    """
    تحويل عام من أي نوع تعبئة لأي نوع تاني (بيج باج<->شكارة، شكارة<->شكارة، حتى سوائل)
    """
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


# ═══════════ Sampling System (نظام العينات الجديد) ═══════════

class PlantLotSetting(models.Model):
    """
    إعداد كل مصنع لطريقة توليد كود العينة (C11(999)...) - عداد الدورة والتسلسل
    """
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
    reset_threshold = models.IntegerField(
        default=9999,
        help_text="لما الرقم التسلسلي يوصل للرقم ده، الدورة (Cycle) بتزيد واحد والتسلسل يرجع لـ 1"
    )
    current_cycle = models.IntegerField(default=1)
    current_sequence = models.IntegerField(default=0)

    class Meta:
        db_table = "factory_plant_lot_settings"

    def __str__(self):
        return f"{self.plant.plant_code} - C{self.current_cycle}"

    @transaction.atomic
    def next_sequence(self):
        """بيرجع (cycle, sequence) الجايين، ويحدّث العداد نفسه بشكل آمن للتزامن"""
        setting = PlantLotSetting.objects.select_for_update().get(pk=self.pk)
        next_seq = setting.current_sequence + 1
        if next_seq > setting.reset_threshold:
            setting.current_cycle += 1
            next_seq = 1
        setting.current_sequence = next_seq
        setting.save(update_fields=["current_cycle", "current_sequence"])
        return setting.current_cycle, setting.current_sequence


class Ton(models.Model):
    """الطن المفرد - وحدة القياس الأساسية اللي بياخد كود مستقل"""
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="tons")
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
    """العينة الممثلة - بتتجمع من طن واحد أو أكتر، وهي اللي بتاخد التحليل الكيميائي الفعلي"""
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="representative_samples")
    cycle_number = models.IntegerField()
    code = models.CharField(max_length=150, blank=True)
    tons = models.ManyToManyField(Ton, related_name="representative_samples")
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "factory_representative_samples"

    def refresh_derived_fields(self):
        """بيتحدث بعد ما تتحدد أو تتعدل الأطنان المكوّنة للعينة"""
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

    def __str__(self):
        return self.code


class TonPhysicalResult(models.Model):
    """نتيجة فيزيائية حقيقية ومستقلة لكل طن (مش منسوخة من حد)"""
    ton = models.ForeignKey(Ton, on_delete=models.CASCADE, related_name="physical_results")
    test = models.ForeignKey(TestDefinition, on_delete=models.PROTECT, related_name="ton_physical_results")
    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_ton_physical_results"
        unique_together = (("ton", "test"),)

    def __str__(self):
        return f"{self.ton.code} - {self.test}: {self.result}"


class SampleChemicalResult(models.Model):
    """
    نتيجة كيميائية بتتسجل على مستوى الممثلة، وبتتنسخ تلقائيًا لكل طن مكوّن ليها.
    is_overridden=True لو الطن ده اتعمله استثناء (إعادة فحص لمتغير معين بمفرده).
    """
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
    قرار الجريد النهائي لكل طن - بيتحدد يدويًا من شخص مسؤول (مش تلقائي دلوقتي)
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

    def __str__(self):
        return f"{self.ton.code} → {self.grade}"