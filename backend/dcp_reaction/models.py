from django.db import models
from plants.models import Plant


class ReactionTankReading(models.Model):
    """
    قراءة/عينة من أي تنك في مرحلة تفاعل DCP (T102 -> Mixer)
    """
    TANK_T102 = "t102"
    TANK_T103 = "t103"
    TANK_T104 = "t104"
    TANK_T150 = "t150"
    TANK_T151 = "t151"
    TANK_T152_AB = "t152_ab"
    TANK_T152_CD = "t152_cd"
    TANK_BELT = "belt"
    TANK_MIXER = "mixer"
    TANK_CHOICES = [
        (TANK_T102, "T102 (خزان الهضم)"),
        (TANK_T103, "T103 (بعد إزالة الرمل)"),
        (TANK_T104, "T104 (نقطة فحص موازية)"),
        (TANK_T150, "T150 (خزان الفلتريت)"),
        (TANK_T151, "T151 (خزان CaCl2 المركز)"),
        (TANK_T152_AB, "T152 (A & B)"),
        (TANK_T152_CD, "T152 (C & D)"),
        (TANK_BELT, "Belt (حزام الوزن)"),
        (TANK_MIXER, "Mixer (المخلط المستمر)"),
    ]

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="dcp_reaction_readings")
    tank_code = models.CharField(max_length=10, choices=TANK_CHOICES)
    sampled_at = models.DateTimeField()

    ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fluoride_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    solid_content_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p2o5_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tss_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    density = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    cacl2_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mc_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    transferred_to_gcc2_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcp_reaction_tank_readings"
        ordering = ["-sampled_at"]

    def __str__(self):
        return f"{self.get_tank_code_display()} - {self.sampled_at:%Y-%m-%d %H:%M}"