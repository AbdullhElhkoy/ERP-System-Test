from django.contrib import admin
from custom_permissions.admin_mixins import PlantScopedAdminMixin
from .models import ReactionTankReading


@admin.register(ReactionTankReading)
class ReactionTankReadingAdmin(PlantScopedAdminMixin, admin.ModelAdmin):
    plant_lookup_field = "plant"
    list_display = ("tank_code", "sampled_at", "ph", "p2o5_percentage", "cacl2_percentage", "mc_percentage")
    list_filter = ("tank_code",)
    ordering = ("-sampled_at",)