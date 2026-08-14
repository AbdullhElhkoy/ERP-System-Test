from django.db import models
from plants.models import Plant
from shared_definitions.models import QualityGrade


class TestDefinition(models.Model):
    CATEGORY_CHEMICAL = "chemical"
    CATEGORY_PHYSICAL = "physical"
    CATEGORY_CHOICES = [
        (CATEGORY_CHEMICAL, "كيميائي"),
        (CATEGORY_PHYSICAL, "فيزيائي"),
    ]

    SCOPE_REACTION = "reaction"
    SCOPE_FINAL_PRODUCT = "final_product"
    SCOPE_CHOICES = [
        (SCOPE_REACTION, "التفاعل (Reaction)"),
        (SCOPE_FINAL_PRODUCT, "المنتج النهائي (Final Product)"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_test_definitions")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default=SCOPE_FINAL_PRODUCT)
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
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_grades")
    code = models.CharField(max_length=20)
    classification = models.ForeignKey(QualityGrade, on_delete=models.PROTECT, related_name="grades")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="الجريد الأساسي الذي يتبع له هذا الثانوي (اتركه فارغاً إذا كان الجريد أساسياً)",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "factory_grades"
        unique_together = (("plant", "code"),)

    def __str__(self):
        if self.parent_id:
            return f"{self.parent.code} / {self.code}"
        return self.code