from django.db import models
from django.utils.translation import gettext_lazy as _
from plants.models import Plant
from shared_definitions.models import QualityGrade


class TestDefinition(models.Model):
    CATEGORY_CHEMICAL = "chemical"
    CATEGORY_PHYSICAL = "physical"
    CATEGORY_CHOICES = [
        (CATEGORY_CHEMICAL, _("Chemical")),
        (CATEGORY_PHYSICAL, _("Physical")),
    ]

    SCOPE_REACTION = "reaction"
    SCOPE_FINAL_PRODUCT = "final_product"
    SCOPE_CHOICES = [
        (SCOPE_REACTION, _("Reaction")),
        (SCOPE_FINAL_PRODUCT, _("Final Product")),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_test_definitions")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    scopes = models.JSONField(default=list, verbose_name=_("Scopes"))
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "factory_test_definitions"
        unique_together = (("plant", "name"),)

    def scopes_display(self):
        labels = dict(self.SCOPE_CHOICES)
        return "، ".join(labels.get(s, s) for s in (self.scopes or []))

    def is_reaction(self):
        return self.SCOPE_REACTION in (self.scopes or [])

    def is_final_product(self):
        return self.SCOPE_FINAL_PRODUCT in (self.scopes or [])

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
        ordering = ["id"]
        unique_together = (("plant", "name"),)

    def __str__(self):
        return self.name


class ConformityRule(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_conformity_rules")
    name = models.CharField(max_length=100)
    quality_grade = models.ForeignKey(QualityGrade, on_delete=models.PROTECT, related_name="conformity_rules")
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=30, blank=True, default="")
    test = models.ForeignKey(
        "factory.TestDefinition", on_delete=models.SET_NULL, null=True, blank=True
    )
    min_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "factory_conformity_rules"
        unique_together = (("plant", "name"),)

    def __str__(self):
        return f"{self.name} -> {self.quality_grade}"


class Grade(models.Model):
    TYPE_PRIMARY = "primary"
    TYPE_SECONDARY = "secondary"
    TYPE_CHOICES = [
        (TYPE_PRIMARY, _("Primary")),
        (TYPE_SECONDARY, _("Secondary")),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="factory_grades")
    code = models.CharField(max_length=20)
    grade_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_PRIMARY,
        verbose_name=_("Grade Type"),
        help_text=_("Primary = shows in primary grade column, Secondary = shows in secondary grade column"),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "factory_grades"
        unique_together = (("plant", "code"),)

    def __str__(self):
        return self.code