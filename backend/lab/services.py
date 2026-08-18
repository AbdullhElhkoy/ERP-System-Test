import random
import string
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from plants.models import Department, DepartmentPlantScope

from .models import Sample, SampleRequiredTest, SampleTestResult


def _generate_sample_code():
    """Generate a unique sample code: LAB-YYYYMMDD-XXXX."""
    date_part = timezone.now().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.digits, k=4))
    code = f"LAB-{date_part}-{rand_part}"
    while Sample.objects.filter(sample_code=code).exists():
        rand_part = "".join(random.choices(string.digits, k=4))
        code = f"LAB-{date_part}-{rand_part}"
    return code


def _resolve_lab_department(plant):
    """Find a lab-type department scoped to this plant."""
    dept_ids = DepartmentPlantScope.objects.filter(
        plant=plant, department__category="lab"
    ).values_list("department_id", flat=True)
    return Department.objects.filter(department_id__in=dept_ids).first()


def create_sample(source_type, source_object, plant, required_tests, collected_by=None, group=None):
    """
    Single entry point for any app to open a new lab sample.

    required_tests: list of dicts [{"name": "SiO2", "test_object": <model_instance>}, ...]
        or legacy [{"name": "SiO2", "id_ref": 123}, ...] (stored as test_name only).
    Returns the created Sample instance.
    """
    ct = ContentType.objects.get_for_model(source_object) if source_object else None
    obj_id = source_object.pk if source_object else None

    sample = Sample.objects.create(
        sample_code=_generate_sample_code(),
        source_type=source_type,
        content_type=ct,
        object_id=obj_id,
        plant=plant,
        lab_department=_resolve_lab_department(plant),
        group=group,
        status=Sample.STATUS_DRAFT,
    )

    for test_info in required_tests:
        test_obj = test_info.get("test_object")
        if test_obj:
            test_ct = ContentType.objects.get_for_model(test_obj)
            test_oid = test_obj.pk
        else:
            test_ct = None
            test_oid = None

        SampleRequiredTest.objects.create(
            sample=sample,
            test_name=test_info["name"],
            test_content_type=test_ct,
            test_object_id=test_oid,
        )

    return sample


def mark_collected(sample, user):
    """Transition sample to 'collected' status."""
    sample.status = Sample.STATUS_COLLECTED
    sample.collected_at = timezone.now()
    sample.collected_by = user
    sample.save(update_fields=["status", "collected_at", "collected_by"])
    return sample


def enter_result(sample, test_name, value, user, test_object=None):
    """
    Record a test result. Update SampleRequiredTest.is_completed.
    test_object: the actual TestDefinition / MaterialTest / InspectionTemplate instance.
    If all required tests are completed → status=ready_for_decision.
    """
    srt = SampleRequiredTest.objects.filter(sample=sample, test_name=test_name).first()

    test_ct = None
    test_oid = None
    if test_object:
        test_ct = ContentType.objects.get_for_model(test_object)
        test_oid = test_object.pk

    if not srt:
        srt = SampleRequiredTest.objects.create(
            sample=sample, test_name=test_name,
            test_content_type=test_ct, test_object_id=test_oid,
        )

    SampleTestResult.objects.update_or_create(
        sample=sample,
        test_name=test_name,
        defaults={"result": value, "entered_by": user,
                  "test_content_type": test_ct, "test_object_id": test_oid},
    )

    srt.is_completed = True
    srt.save(update_fields=["is_completed"])

    sample.refresh_from_db()
    all_done = not sample.required_tests.filter(is_completed=False).exists()
    if all_done and sample.status not in (Sample.STATUS_READY_FOR_DECISION, Sample.STATUS_DECIDED):
        sample.status = Sample.STATUS_READY_FOR_DECISION
        sample.ready_for_decision_at = timezone.now()
        sample.save(update_fields=["status", "ready_for_decision_at"])

    return sample
