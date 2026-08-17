from decimal import Decimal
from django.db import models
from django.db.models import Sum, Case, When, DecimalField


class Material(models.Model):
    """
    جميع خامات الشركة.
    """
    material_code = models.CharField(max_length=20, unique=True)
    material_name = models.CharField(max_length=100)
    description   = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)

    class Meta:
        db_table = "materials"
        ordering = ["material_name"]

    def __str__(self):
        return self.material_name


class Supplier(models.Model):
    """
    الموردين المعتمدين.
    """
    supplier_code = models.CharField(max_length=20, unique=True)
    supplier_name = models.CharField(max_length=150)
    phone         = models.CharField(max_length=30, blank=True)
    email         = models.EmailField(blank=True)
    address       = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)

    class Meta:
        db_table = "suppliers"
        ordering = ["supplier_name"]

    def __str__(self):
        return self.supplier_name


class MaterialTest(models.Model):
    """
    الاختبارات الممكنة لكل خام.
    """
    material  = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="tests",
    )
    test_code = models.CharField(max_length=30, unique=True)
    test_name = models.CharField(max_length=100)
    unit      = models.CharField(max_length=20)

    class Meta:
        db_table = "material_tests"
        ordering  = ["material", "test_name"]

    def __str__(self):
        return f"{self.material.material_name} - {self.test_name}"


class MaterialSpecification(models.Model):
    """
    مواصفة كل خام لكل اختبار.
    """
    material          = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="specifications")
    test              = models.ForeignKey(MaterialTest, on_delete=models.CASCADE, related_name="specifications")
    specification_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    specification_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    is_active         = models.BooleanField(default=True)
    notes             = models.TextField(blank=True)

    class Meta:
        db_table      = "material_specifications"
        unique_together = (("material", "test"),)
        ordering      = ["material", "test"]

    def __str__(self):
        return f"{self.material} - {self.test}"


class MaterialStorage(models.Model):
    """
    مخزن خام داخل مصنع.
    يمثل مكان تجميع الخام (Bulk Storage).
    """

    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.PROTECT,
        related_name="material_storages",
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="storages",
    )

    storage_code = models.CharField(
        max_length=30,
        unique=True,
    )

    storage_name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    allow_estimated_issue = models.BooleanField(
        default=False,
        help_text="يسمح بتسجيل عمليات صرف تقديرية (Estimated) من المخزن ده بدل الدقيقة بس",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "material_storages"
        ordering = ["plant", "material", "storage_name"]
        unique_together = (("plant", "material", "storage_name"),)

    @property
    def current_balance(self):
        """
        الرصيد الحالي للمخزن.
        الرصيد = الوارد - المنصرف + التسويات.
        """

        totals = self.transactions.aggregate(
            incoming=Sum(
                Case(
                    When(
                        movement_type=InventoryTransaction.MOVEMENT_IN,
                        then="quantity_tons",
                    ),
                    default=Decimal("0"),
                    output_field=DecimalField(),
                )
            ),
            outgoing=Sum(
                Case(
                    When(
                        movement_type=InventoryTransaction.MOVEMENT_OUT,
                        then="quantity_tons",
                    ),
                    default=Decimal("0"),
                    output_field=DecimalField(),
                )
            ),
            adjustments=Sum(
                Case(
                    When(
                        movement_type=InventoryTransaction.MOVEMENT_ADJUSTMENT,
                        then="quantity_tons",
                    ),
                    default=Decimal("0"),
                    output_field=DecimalField(),
                )
            ),
        )

        return (
            (totals["incoming"] or Decimal("0"))
            - (totals["outgoing"] or Decimal("0"))
            + (totals["adjustments"] or Decimal("0"))
        )

    def __str__(self):
        return (
            f"{self.plant.plant_name} - "
            f"{self.material.material_name} - "
            f"{self.storage_name}"
        )


class RawMaterialDelivery(models.Model):
    """
    استلام شحنة خام.
    """
    DECISION_ACCEPTED              = "accepted"
    DECISION_REJECTED              = "rejected"
    DECISION_ACCEPTED_WITH_DEDUCTION = "accepted_with_deduction"

    DECISION_CHOICES = [
        (DECISION_ACCEPTED,               "مقبولة"),
        (DECISION_REJECTED,               "مرفوضة"),
        (DECISION_ACCEPTED_WITH_DEDUCTION, "مقبولة بخصم"),
    ]

    plant    = models.ForeignKey('plants.Plant',    on_delete=models.PROTECT, related_name="raw_material_deliveries")
    material = models.ForeignKey(Material,          on_delete=models.PROTECT, related_name="deliveries")
    supplier = models.ForeignKey(Supplier,          on_delete=models.PROTECT, related_name="deliveries")
    storage  = models.ForeignKey(MaterialStorage,   on_delete=models.PROTECT, related_name="deliveries", null=True, blank=True)
    vehicle_number       = models.CharField(max_length=30)
    weight_tons          = models.DecimalField(max_digits=8, decimal_places=3)
    arrived_at           = models.DateTimeField()
    decision             = models.CharField(max_length=25, choices=DECISION_CHOICES)
    deduction_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes                = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raw_material_deliveries"
        ordering = ["-arrived_at"]

    def save(self, *args, **kwargs):
        """
        بتحسب effective_weight بعد تطبيق نسبة الخصم (لو موجودة)
        قبل ما تعمل حركة مخزون تلقائية.
        """
        from decimal import Decimal

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.decision != self.DECISION_REJECTED:
            effective_weight = self.weight_tons
            if (
                self.decision == self.DECISION_ACCEPTED_WITH_DEDUCTION
                and self.deduction_percentage is not None
                and self.deduction_percentage > 0
            ):
                effective_weight = self.weight_tons * (
                    1 - self.deduction_percentage / Decimal('100')
                )

            InventoryTransaction.objects.create(
                material         = self.material,
                plant            = self.plant,
                storage          = self.storage,
                movement_type    = InventoryTransaction.MOVEMENT_IN,
                accuracy_type    = InventoryTransaction.ACCURACY_EXACT,
                quantity_tons    = effective_weight,
                transaction_date = self.arrived_at,
                reference_delivery = self,
                notes            = "تم الإنشاء تلقائياً من استلام الشحنة",
            )

    def clean(self):
        from django.core.exceptions import ValidationError
        if (
            self.decision in (self.DECISION_ACCEPTED, self.DECISION_ACCEPTED_WITH_DEDUCTION)
            and not self.storage_id
        ):
            raise ValidationError({
                "storage": "لازم تحدد المخزن لو الشحنة مقبولة أو مقبولة بخصم."
            })

    def __str__(self):
        return f"{self.material.material_name} - {self.vehicle_number}"


class InventoryTransaction(models.Model):
    """
    حركة مخزون لأي خام داخل الشركة.
    """
    MOVEMENT_IN         = "in"
    MOVEMENT_OUT        = "out"
    MOVEMENT_ADJUSTMENT = "adjustment"
    MOVEMENT_CHOICES    = [
        (MOVEMENT_IN,         "إضافة"),
        (MOVEMENT_OUT,        "صرف"),
        (MOVEMENT_ADJUSTMENT, "تسوية"),
    ]

    ACCURACY_EXACT     = "exact"
    ACCURACY_ESTIMATED = "estimated"
    ACCURACY_CHOICES   = [
        (ACCURACY_EXACT,     "دقيق"),
        (ACCURACY_ESTIMATED, "تقديري"),
    ]

    material    = models.ForeignKey(Material,         on_delete=models.PROTECT, related_name="inventory_transactions")
    plant       = models.ForeignKey('plants.Plant',   on_delete=models.PROTECT, related_name="inventory_transactions")
    storage     = models.ForeignKey(MaterialStorage,  on_delete=models.PROTECT, related_name="transactions")
    movement_type  = models.CharField(max_length=20, choices=MOVEMENT_CHOICES)
    accuracy_type  = models.CharField(max_length=20, choices=ACCURACY_CHOICES, default=ACCURACY_EXACT)
    quantity_tons  = models.DecimalField(max_digits=12, decimal_places=3)
    transaction_date = models.DateTimeField()

    reference_delivery = models.ForeignKey(
        RawMaterialDelivery,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_transactions",
    )

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transactions"
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"{self.material.material_name} - {self.get_movement_type_display()} - {self.quantity_tons} طن"


class RawMaterialLot(models.Model):
    """
    التشغيلة الناتجة من استلام خام.
    """
    delivery          = models.ForeignKey(RawMaterialDelivery, on_delete=models.PROTECT, related_name="lots")
    lot_number        = models.CharField(max_length=50, unique=True)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raw_material_lots"
        ordering = ["-created_at"]

    def __str__(self):
        return self.lot_number


class RawMaterialSample(models.Model):
    """
    عينة مسحوبة أثناء أي مرحلة من مراحل تداول الخامة.
    """
    STAGE_RECEIPT      = "receipt"
    STAGE_PRE_MILLING  = "pre_milling"
    STAGE_POST_MILLING = "post_milling"
    STAGE_CHOICES = [
        (STAGE_RECEIPT,      "عند الاستلام"),
        (STAGE_PRE_MILLING,  "قبل الطحن"),
        (STAGE_POST_MILLING, "بعد الطحن"),
    ]

    sample_stage = models.CharField(max_length=15, choices=STAGE_CHOICES, default=STAGE_RECEIPT)
    plant        = models.ForeignKey('plants.Plant', on_delete=models.PROTECT, related_name="raw_material_samples")
    material     = models.ForeignKey(Material,       on_delete=models.PROTECT, related_name="samples")

    delivery = models.ForeignKey(
        RawMaterialDelivery,
        on_delete=models.CASCADE,
        related_name="samples",
        null=True, blank=True,
        help_text="إجباري بس لو المرحلة (عند الاستلام)، فاضي في حالة قبل/بعد الطحن",
    )

    sample_number = models.PositiveIntegerField()
    sampled_at    = models.DateTimeField()
    sampled_by    = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)
    lab_sample    = models.OneToOneField(
        "lab.Sample", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="raw_material_sample",
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table       = "raw_material_samples"
        ordering       = ["sampled_at"]
        unique_together = (("plant", "material", "sample_stage", "sample_number"),)

    def __str__(self):
        return f"{self.material.material_name} - {self.get_sample_stage_display()} - Sample {self.sample_number}"


class RawMaterialAnalysis(models.Model):
    """
    نتيجة اختبار واحد لعينة.
    كل صف = اختبار واحد.
    """
    sample        = models.ForeignKey(RawMaterialSample, on_delete=models.CASCADE,  related_name="analyses")
    test          = models.ForeignKey(MaterialTest,       on_delete=models.PROTECT,  related_name="results")
    result        = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    is_conforming = models.BooleanField(null=True, blank=True)
    remarks       = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table       = "raw_material_analysis"
        ordering       = ["sample", "test"]
        unique_together = (("sample", "test"),)

    def save(self, *args, **kwargs):
        specification = (
            MaterialSpecification.objects
            .filter(
                material  = self.sample.material,
                test      = self.test,
                is_active = True,
            )
            .first()
        )

        if specification and self.result is not None:
            ok = True
            if (
                specification.specification_min is not None
                and self.result < specification.specification_min
            ):
                ok = False
            if (
                specification.specification_max is not None
                and self.result > specification.specification_max
            ):
                ok = False
            self.is_conforming = ok
        else:
            self.is_conforming = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sample} - {self.test.test_name}"