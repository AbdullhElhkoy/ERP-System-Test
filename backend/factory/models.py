from django.db import models
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

    def __str__(self):
        return f"{self.name} -> {self.quality_grade}"


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
    quality_grade = models.ForeignKey(QualityGrade, on_delete=models.PROTECT, related_name="conformity_results")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "factory_quality_conformity_results"

    def __str__(self):
        return f"{self.reading} -> {self.quality_grade}"


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