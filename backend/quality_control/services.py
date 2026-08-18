from decimal import Decimal
from custom_permissions.services import can_edit_column
from lab.models import Sample

from .models import QualityDecision


def compute_suggested_decision(sample):
    """
    Compare each SampleTestResult against matching ConformityRules.
    Returns (decision, rule) or (None, None) if no rule matches.
    """
    from factory.models import ConformityRule
    from lab.models import SampleTestResult

    rules = ConformityRule.objects.filter(
        source_type=sample.source_type,
        test__isnull=False,
    ).select_related("test", "quality_grade")

    for rule in rules:
        result = SampleTestResult.objects.filter(
            sample=sample, test_name=rule.test.name
        ).first()
        if not result or result.result is None:
            continue

        value = result.result
        if rule.min_value is not None and value < rule.min_value:
            return (QualityDecision.REJECT, rule)
        if rule.max_value is not None and value > rule.max_value:
            return (QualityDecision.REJECT, rule)

    return (None, None)


def approve_decision(sample, user, final_decision, reason=""):
    """
    Approve a QC decision for a sample.

    - Checks can_edit_column (fail-closed if no permission).
    - Creates/updates QualityDecision.
    - Updates sample.status = 'decided'.
    """
    if not user.is_superuser:
        if not can_edit_column(user, "lab_sample_sheet", "qc_decision"):
            raise PermissionError("You do not have permission to approve QC decisions.")

    suggested, rule = compute_suggested_decision(sample)

    decision, _ = QualityDecision.objects.update_or_create(
        sample=sample,
        defaults={
            "suggested_decision": suggested or "",
            "suggested_by_rule": rule,
            "final_decision": final_decision,
            "decided_by": user,
            "reason": reason,
        },
    )

    sample.status = Sample.STATUS_DECIDED
    sample.save(update_fields=["status"])

    return decision
