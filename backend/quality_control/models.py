from django.conf import settings
from django.db import models


class QualityDecision(models.Model):
    """QC decision for a lab sample — one decision per sample."""
    DECISION_CONFORM = "conform"
    DECISION_CONFORM_WITH_DEDUCTION = "conform_with_deduction"
    DECISION_REJECT = "reject"
    DECISION_HOLD = "hold"
    DECISION_CHOICES = [
        (DECISION_CONFORM, "Conform"),
        (DECISION_CONFORM_WITH_DEDUCTION, "Conform with Deduction"),
        (DECISION_REJECT, "Reject"),
        (DECISION_HOLD, "Hold"),
    ]

    sample = models.OneToOneField(
        "lab.Sample", on_delete=models.CASCADE, related_name="quality_decision"
    )
    suggested_decision = models.CharField(max_length=30, choices=DECISION_CHOICES, blank=True)
    suggested_by_rule = models.ForeignKey(
        "factory.ConformityRule", on_delete=models.SET_NULL, null=True, blank=True
    )
    final_decision = models.CharField(max_length=30, choices=DECISION_CHOICES)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = "quality_control_decisions"

    def __str__(self):
        return f"{self.sample.sample_code} → {self.final_decision}"
