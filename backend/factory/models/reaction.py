from django.db import models
from plants.models import Plant
from .shared import TestDefinition


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