from django.db import models


class FieldDefinition(models.Model):
    """
    مكتبة الحقول الشاملة (Master Fields Pool)
    مشتركة لكل الشركة - مش لكل مصنع لوحده
    """
    TYPE_NUMBER = "number"
    TYPE_INTEGER = "integer"
    TYPE_TEXT = "text"
    TYPE_DATE = "date"
    TYPE_CHOICE = "choice"
    FIELD_TYPE_CHOICES = [
        (TYPE_NUMBER, "رقم عشري"),
        (TYPE_INTEGER, "رقم صحيح"),
        (TYPE_TEXT, "نص"),
        (TYPE_DATE, "تاريخ"),
        (TYPE_CHOICE, "اختيار من قائمة"),
    ]

    CATEGORY_BASIC = "basic"
    CATEGORY_CHEMICAL = "chemical"
    CATEGORY_PHYSICAL = "physical"
    CATEGORY_GENERAL = "general"
    CATEGORY_CHOICES = [
        (CATEGORY_BASIC, "أساسي (وزن / كمية)"),
        (CATEGORY_CHEMICAL, "فحص كيميائي"),
        (CATEGORY_PHYSICAL, "فحص فيزيائي"),
        (CATEGORY_GENERAL, "بيانات عامة"),
    ]

    key = models.SlugField(max_length=50, unique=True, help_text="معرف فريد بالإنجليزي بدون مسافات، يستخدم داخليًا (مثال: batch_number)")
    name = models.CharField(max_length=100, help_text="الاسم اللي هيظهر للمستخدم")
    field_type = models.CharField(max_length=15, choices=FIELD_TYPE_CHOICES)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
    unit = models.CharField(max_length=20, blank=True)
    choices = models.JSONField(blank=True, null=True, help_text="لنوع 'اختيار من قائمة' فقط - قائمة بالخيارات")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "factory_field_definitions"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.unit})" if self.unit else self.name


class PackingTypeField(models.Model):
    """
    ربط الحقول المفعّلة بكل نوع تعبئة (Packaging Type Configuration)
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
