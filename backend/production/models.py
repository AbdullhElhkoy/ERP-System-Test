from django.db import models
from django.core.exceptions import ValidationError
from plants.models import Plant


class ProductionRun(models.Model):
    """
    التشغيلة: كمية 1000 طن، بتاخد من 4 لـ 6 شهور على حسب الإنتاجية.
    """
    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT, related_name="production_runs"
    )
    run_number = models.PositiveIntegerField(
        help_text="رقم التشغيلة (1، 2، 3...) لكل مصنع"
    )
    started_at = models.DateField()
    ended_at = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("plant", "run_number")
        ordering = ["plant", "run_number"]
        verbose_name = "Production Run (تشغيلة)"
        verbose_name_plural = "Production Runs (تشغيلات)"

    def __str__(self):
        return f"{self.plant.plant_code} - تشغيلة {self.run_number}"


class Silo(models.Model):
    """
    السيلو: مرتبط بمصنع معين، وده اللي بيخرج منه المنتج.
    """
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="silos")
    code = models.CharField(max_length=10, help_text="مثال: A, B, C")

    class Meta:
        unique_together = ("plant", "code")
        verbose_name = "Silo (سيلو)"
        verbose_name_plural = "Silos (سيلوهات)"

    def __str__(self):
        return f"{self.plant.plant_code} - سيلو {self.code}"


class ProductionBatch(models.Model):
    """
    كود الجودة (Quality/Production Batch):
    تسلسلي، مرتبط بسيلو معين ورقم تشغيلة معين.
    """
    sequence_number = models.PositiveIntegerField(
        unique=True,
        help_text="الرقم التسلسلي لكود الجودة (1, 2, 3, 4, 5...)"
    )
    silo = models.ForeignKey(
        Silo, on_delete=models.PROTECT, related_name="production_batches"
    )
    production_run = models.ForeignKey(
        ProductionRun, on_delete=models.PROTECT, related_name="production_batches"
    )
    produced_at = models.DateTimeField()

    class Meta:
        ordering = ["sequence_number"]
        verbose_name = "Production Batch (كود الجودة)"
        verbose_name_plural = "Production Batches (أكواد الجودة)"

    def __str__(self):
        return f"QC-{self.sequence_number} ({self.silo})"


class BigBag(models.Model):
    """
    بيج باج فردي 1000 كيلو.
    الحالة بتتغير مرة واحدة بس: SEALED -> SOLD_WHOLE أو SEALED -> CONVERTED_TO_SACKS
    """

    class Status(models.TextChoices):
        SEALED = "SEALED", "مقفول (في المخزن)"
        SOLD_WHOLE = "SOLD_WHOLE", "اتباع كامل"
        CONVERTED_TO_SACKS = "CONVERTED_TO_SACKS", "اتحول لشكاير"

    bag_number = models.PositiveIntegerField(
        unique=True, help_text="الرقم التسلسلي للبيج باج"
    )
    production_batch = models.ForeignKey(
        ProductionBatch, on_delete=models.PROTECT, related_name="big_bags"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SEALED
    )
    packed_at = models.DateTimeField()

    class Meta:
        ordering = ["bag_number"]
        verbose_name = "Big Bag (بيج باج)"
        verbose_name_plural = "Big Bags (بيج باجات)"

    def __str__(self):
        return f"BigBag #{self.bag_number} ({self.get_status_display()})" #type: igonor
    def clean(self):
        if self.pk:
            original = BigBag.objects.get(pk=self.pk)
            if original.status != self.Status.SEALED and original.status != self.status:
                raise ValidationError(
                    "لا يمكن تغيير حالة بيج باج بعد ما يتباع كامل أو يتحول لشكاير."
                )


class SackType(models.Model):
    """
    نوع/حجم الشكارة، قابل للتهيئة من الإعدادات (25kg, 30kg, 35kg...).
    """
    name = models.CharField(max_length=30, unique=True, help_text="مثال: شكارة 25 كيلو")
    nominal_weight_kg = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        verbose_name = "Sack Type (نوع الشكارة)"
        verbose_name_plural = "Sack Types (أنواع الشكاير)"

    def __str__(self):
        return self.name


class SackConversion(models.Model):
    """
    تحويل بيج باج كامل لعدد شكاير - يحصل مرة واحدة فقط لكل بيج باج،
    وبيربط بمصدر واحد بس (البيج باج الأصلي).
    """
    big_bag = models.OneToOneField(
        BigBag, on_delete=models.PROTECT, related_name="sack_conversion"
    )
    sack_type = models.ForeignKey(
        SackType, on_delete=models.PROTECT, related_name="conversions"
    )
    sack_count = models.PositiveIntegerField(help_text="عدد الشكاير الناتجة، مثلاً 40")
    converted_at = models.DateTimeField()

    class Meta:
        verbose_name = "Sack Conversion (تحويل لشكاير)"
        verbose_name_plural = "Sack Conversions (تحويلات لشكاير)"

    def __str__(self):
        return f"{self.big_bag} -> {self.sack_count} x {self.sack_type}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.big_bag.status = BigBag.Status.CONVERTED_TO_SACKS
        self.big_bag.save(update_fields=["status"])


class Customer(models.Model):
    """
    عميل بسيط - ممكن يتوسع لاحقاً في موديل Sales الخاص به.
    """
    name = models.CharField(max_length=150)
    is_export = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Customer (عميل)"
        verbose_name_plural = "Customers (عملاء)"

    def __str__(self):
        return self.name


class OrderBatch(models.Model):
    """
    باتش الطلبية - بيربط بيج باجات كاملة و/أو تحويلات شكاير معينة بطلبية عميل.
    الوزن بيتسجل على مستوى الطلبية ككل، مش على مستوى الوحدة الفردية.
    """
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="order_batches"
    )
    order_reference = models.CharField(max_length=50, unique=True)
    total_weight_kg = models.DecimalField(max_digits=12, decimal_places=2)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    whole_big_bags = models.ManyToManyField(
        BigBag, blank=True, related_name="order_batches",
        help_text="البيج باجات اللي اتباعت كاملة في الطلبية دي"
    )
    sack_conversions = models.ManyToManyField(
        SackConversion, blank=True, related_name="order_batches",
        help_text="تحويلات الشكاير اللي اتباع منها في الطلبية دي"
    )

    class Meta:
        ordering = ["-dispatched_at"]
        verbose_name = "Order Batch (باتش الطلبية)"
        verbose_name_plural = "Order Batches (أكواد الطلبيات)"

    def __str__(self):
        return f"Order {self.order_reference} - {self.customer}"