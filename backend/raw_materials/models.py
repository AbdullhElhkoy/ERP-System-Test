from django.db import models
from plants.models import Plant


class RawMaterialDelivery(models.Model):
    """
    استلام عربية مادة خام: HCl، صخر الفوسفات، أو CaCO3
    """
    MATERIAL_HCL = "hcl"
    MATERIAL_PHOSPHATE_ROCK = "phosphate_rock"
    MATERIAL_CACO3 = "caco3"
    MATERIAL_CHOICES = [
        (MATERIAL_HCL, "حمض الهيدروكلوريك (HCl)"),
        (MATERIAL_PHOSPHATE_ROCK, "صخر الفوسفات"),
        (MATERIAL_CACO3, "كربونات الكالسيوم (CaCO3)"),
    ]

    DECISION_ACCEPTED = "accepted"
    DECISION_REJECTED = "rejected"
    DECISION_ACCEPTED_WITH_DEDUCTION = "accepted_with_deduction"
    DECISION_CHOICES = [
        (DECISION_ACCEPTED, "مقبولة"),
        (DECISION_REJECTED, "مرفوضة"),
        (DECISION_ACCEPTED_WITH_DEDUCTION, "مقبولة بخصم"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="raw_material_deliveries")
    material_type = models.CharField(max_length=20, choices=MATERIAL_CHOICES)

    supplier_name = models.CharField(max_length=100)
    vehicle_number = models.CharField(max_length=30)
    weight_tons = models.DecimalField(max_digits=8, decimal_places=3)
    arrived_at = models.DateTimeField()

    decision = models.CharField(max_length=25, choices=DECISION_CHOICES)
    deduction_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # تحليل HCl
    hcl_concentration_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # تحليل صخر الفوسفات و CaCO3 (مشتركين)
    p2o5_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    impurities_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # تحليل CaCO3 بس
    purity_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raw_material_deliveries"
        ordering = ["-arrived_at"]

    def __str__(self):
        return f"{self.get_material_type_display()} - {self.vehicle_number} - {self.plant.plant_code}"


class PreMillingSample(models.Model):
    """
    عينة ما قبل الطحن - مش مرتبطة بعربية واحدة بعينها (المخزن مخلوط من عدة عربيات)
    """
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="pre_milling_samples")
    sampled_at = models.DateTimeField()

    p2o5_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    impurities_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pre_milling_samples"
        ordering = ["-sampled_at"]

    def __str__(self):
        return f"عينة ما قبل الطحن - {self.plant.plant_code} - {self.sampled_at:%Y-%m-%d %H:%M}"


class PostMillingSample(models.Model):
    """
    عينة ما بعد الطحن - شاملة تحليل المناخل (Sieve Analysis)
    """
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="post_milling_samples")
    sampled_at = models.DateTimeField()

    p2o5_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    impurities_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    sieve_over_5mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sieve_over_2mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sieve_over_1mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sieve_over_0_5mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sieve_under_0_5mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_milling_samples"
        ordering = ["-sampled_at"]

    def __str__(self):
        return f"عينة ما بعد الطحن - {self.plant.plant_code} - {self.sampled_at:%Y-%m-%d %H:%M}"