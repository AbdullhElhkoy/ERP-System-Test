import math
from django.db import models
from plants.models import Plant

QUALITY_PRESENT = "present"
QUALITY_SLIGHT = "slight"
QUALITY_ABSENT = "absent"
QUALITY_CHOICES = [
    (QUALITY_PRESENT, "موجود"),
    (QUALITY_SLIGHT, "موجود بنسبة بسيطة"),
    (QUALITY_ABSENT, "غير موجود"),
]

# خيارات لون القفيز
QAFEEZ_GREEN = "green"
QAFEEZ_YELLOW = "yellow"
QAFEEZ_GREEN_YELLOW = "green_yellow"
QAFEEZ_BLUE = "blue"
QAFEEZ_WHITE = "white"
QAFEEZ_RED = "red"
QAFEEZ_COLOR_CHOICES = [
    (QAFEEZ_GREEN, "Green"),
    (QAFEEZ_YELLOW, "Yellow"),
    (QAFEEZ_GREEN_YELLOW, "Green & Yellow"),
    (QAFEEZ_BLUE, "Blue"),
    (QAFEEZ_WHITE, "White"),
    (QAFEEZ_RED, "Red"),
]


class FinalProductSiloReading(models.Model):
    SILO_A = "a"
    SILO_B = "b"
    SILO_C = "c"
    SILO_CHOICES = [
        (SILO_A, "سيلو A"),
        (SILO_B, "سيلو B"),
        (SILO_C, "سيلو C"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="dcp_final_silo_readings")
    silo = models.CharField(max_length=1, choices=SILO_CHOICES)
    sampled_at = models.DateTimeField()

    represented_weight_tons = models.PositiveIntegerField(default=4, help_text="الوزن بأرقام صحيحة فقط بدون كسور")
    sequence_number = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="كود الممثلة التلقائي"
    )
    cumulative_weight_tons = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    sample_code = models.CharField(max_length=50, blank=True, editable=False)

    mc_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p2o5_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fluoride_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cl_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    bulk_density = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    total_ca_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcp_final_silo_readings"
        ordering = ["-sampled_at"]

    def save(self, *args, **kwargs):
        if not self.cumulative_weight_tons:
            last = (
                FinalProductSiloReading.objects
                .filter(plant=self.plant)
                .exclude(pk=self.pk)
                .order_by("-id")
                .first()
            )
            previous_cumulative = last.cumulative_weight_tons if last else 0
            self.cumulative_weight_tons = previous_cumulative + self.represented_weight_tons

        super().save(*args, **kwargs)

    def rebuild_sample_code(self):
        cycle_number = math.ceil(float(self.cumulative_weight_tons) / 10000.0) if self.cumulative_weight_tons > 0 else 1
        lot_numbers = self.lots.order_by("lot_number").values_list("lot_number", flat=True)
        lots_part = "+".join(str(n) for n in lot_numbers)
        
        self.sample_code = f"{cycle_number}C ({lots_part}) {self.silo.upper()}"
        self.sequence_number = self.sample_code
        self.save(update_fields=["sample_code", "sequence_number"])

    def __str__(self):
        return self.sample_code or f"سيلو {self.get_silo_display()} - {self.sampled_at:%Y-%m-%d %H:%M}"


class FinalProductSampleLot(models.Model):
    silo_reading = models.ForeignKey(FinalProductSiloReading, on_delete=models.CASCADE, related_name="lots")
    lot_number = models.PositiveIntegerField()

    color_status = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    im_status = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    over_status = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    qafeez_color = models.CharField(
        max_length=15, choices=QAFEEZ_COLOR_CHOICES,
        blank=True, verbose_name="لون القفيز"
    )

    class Meta:
        db_table = "dcp_final_sample_lots"
        ordering = ["lot_number"]
        unique_together = (("silo_reading", "lot_number"),)

    def __str__(self):
        return f"بجزة {self.lot_number}"


class FinalProductPacking(models.Model):
    CONTAINER_BIG_BAG = "big_bag"
    CONTAINER_SMALL_BAG = "small_bag"
    CONTAINER_BULK = "bulk"
    CONTAINER_CHOICES = [
        (CONTAINER_BIG_BAG, "Big Bag"),
        (CONTAINER_SMALL_BAG, "شكارة صغيرة"),
        (CONTAINER_BULK, "Bulk"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="dcp_final_packings")
    source_silo = models.ForeignKey(
        FinalProductSiloReading, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="packings"
    )
    container_type = models.CharField(max_length=15, choices=CONTAINER_CHOICES, default=CONTAINER_BIG_BAG)
    packed_at = models.DateTimeField()
    quantity_tons = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    bags_count = models.PositiveIntegerField(null=True, blank=True)

    post_pack_sample_taken = models.BooleanField(default=False)
    post_pack_sample_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcp_final_packings"
        ordering = ["-packed_at"]

    def __str__(self):
        return f"{self.get_container_type_display()} - {self.packed_at:%Y-%m-%d %H:%M}"


class FinalProductRepacking(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="dcp_final_repackings")
    source_packing = models.ForeignKey(
        FinalProductPacking, on_delete=models.PROTECT, related_name="repackings",
        limit_choices_to={"container_type": FinalProductPacking.CONTAINER_BIG_BAG},
    )
    packed_at = models.DateTimeField()
    quantity_tons = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    bags_count = models.PositiveIntegerField(null=True, blank=True)

    post_pack_sample_taken = models.BooleanField(default=False)
    post_pack_sample_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcp_final_repackings"
        ordering = ["-packed_at"]

    def __str__(self):
        return f"إعادة تعبئة من {self.source_packing} - {self.packed_at:%Y-%m-%d %H:%M}"