from django.db import models
from django.utils.translation import gettext_lazy as _


class FieldDefinition(models.Model):
    """
    Master Fields Pool — shared across the whole company, not per factory.
    """
    TYPE_NUMBER = "number"
    TYPE_INTEGER = "integer"
    TYPE_TEXT = "text"
    TYPE_DATE = "date"
    TYPE_CHOICE = "choice"
    FIELD_TYPE_CHOICES = [
        (TYPE_NUMBER, _("Decimal")),
        (TYPE_INTEGER, _("Integer")),
        (TYPE_TEXT, _("Text")),
        (TYPE_DATE, _("Date")),
        (TYPE_CHOICE, _("Select from list")),
    ]

    CATEGORY_BASIC = "basic"
    CATEGORY_CHEMICAL = "chemical"
    CATEGORY_PHYSICAL = "physical"
    CATEGORY_GENERAL = "general"
    CATEGORY_CHOICES = [
        (CATEGORY_BASIC, _("Basic (Weight / Quantity)")),
        (CATEGORY_CHEMICAL, _("Chemical Test")),
        (CATEGORY_PHYSICAL, _("Physical Test")),
        (CATEGORY_GENERAL, _("General Data")),
    ]

    key = models.SlugField(max_length=50, unique=True, help_text=_("Unique English identifier without spaces, used internally (e.g. batch_number)"))
    name = models.CharField(max_length=100, help_text=_("Name that will be shown to the user"))
    field_type = models.CharField(max_length=15, choices=FIELD_TYPE_CHOICES)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
    unit = models.CharField(max_length=20, blank=True)
    choices = models.JSONField(blank=True, null=True, help_text=_("For 'Select from list' type only — list of choices"))
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "factory_field_definitions"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.unit})" if self.unit else self.name


class PackingTypeField(models.Model):
    """
    Packaging Type Configuration — links active fields to each packing type.
    """
    packing_type = models.ForeignKey(
        "factory.PackingType", on_delete=models.CASCADE, related_name="field_configs"
    )
    field = models.ForeignKey(
        FieldDefinition, on_delete=models.CASCADE, related_name="packing_type_configs"
    )
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = "factory_packing_type_fields"
        unique_together = (("packing_type", "field"),)
        ordering = ["order"]

    def __str__(self):
        return f"{self.packing_type} - {self.field}"
