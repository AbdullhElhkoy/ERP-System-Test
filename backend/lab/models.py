from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


SOURCE_TYPES = [
    ("final_product", "Final Product"),
    ("raw_material", "Raw Material"),
    ("packaging_material", "Packaging Material"),
    ("spare_part", "Spare Part"),
    ("environmental", "Environmental"),
    ("warehouse_stock", "Warehouse Stock"),
    ("order_sample", "Order Sample"),
    ("other", "Other"),
]


class SampleGroup(models.Model):
    """Group samples from the same location/packing type for batch analysis."""
    group_code = models.CharField(max_length=30, unique=True)
    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT)
    location_label = models.CharField(max_length=100)
    packing_type_name = models.CharField(max_length=50, blank=True, default="")
    packing_type_ref = models.PositiveIntegerField(null=True, blank=True, help_text="Reference to factory.PackingType PK")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lab_sample_groups"
        ordering = ["-created_at"]

    def __str__(self):
        return self.group_code


class Sample(models.Model):
    """Central sample entity — links to any source via GenericForeignKey."""
    STATUS_DRAFT = "draft"
    STATUS_COLLECTED = "collected"
    STATUS_UNDER_ANALYSIS = "under_analysis"
    STATUS_RESULTS_ENTERED = "results_entered"
    STATUS_READY_FOR_DECISION = "ready_for_decision"
    STATUS_DECIDED = "decided"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_COLLECTED, "Collected"),
        (STATUS_UNDER_ANALYSIS, "Under Analysis"),
        (STATUS_RESULTS_ENTERED, "Results Entered"),
        (STATUS_READY_FOR_DECISION, "Ready for Decision"),
        (STATUS_DECIDED, "Decided"),
    ]

    sample_code = models.CharField(max_length=30, unique=True)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_object = GenericForeignKey("content_type", "object_id")

    plant = models.ForeignKey("plants.Plant", on_delete=models.PROTECT)
    lab_department = models.ForeignKey(
        "plants.Department", on_delete=models.SET_NULL, null=True, blank=True
    )
    group = models.ForeignKey(
        SampleGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    ready_for_decision_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lab_samples"
        ordering = ["-created_at"]

    def __str__(self):
        return self.sample_code


class SampleRequiredTest(models.Model):
    """Tests required before a sample is considered ready for QC decision."""
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="required_tests")
    test_name = models.CharField(max_length=100)

    test_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_required_tests",
    )
    test_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    test_object = GenericForeignKey("test_content_type", "test_object_id")

    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "lab_sample_required_tests"
        unique_together = (("sample", "test_name"),)

    def __str__(self):
        return f"{self.sample.sample_code} — {self.test_name}"


class SampleTestResult(models.Model):
    """Individual test result for a sample."""
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="test_results")
    test_name = models.CharField(max_length=100)

    test_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_test_results",
    )
    test_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    test_object = GenericForeignKey("test_content_type", "test_object_id")

    result = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    entered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lab_sample_test_results"
        unique_together = (("sample", "test_name"),)

    def __str__(self):
        return f"{self.sample.sample_code} — {self.test_name}: {self.result}"
