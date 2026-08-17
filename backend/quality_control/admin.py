from django.contrib import admin
from .models import QualityDecision


@admin.register(QualityDecision)
class QualityDecisionAdmin(admin.ModelAdmin):
    list_display = ("sample", "final_decision", "suggested_decision", "decided_by", "decided_at")
    list_filter = ("final_decision",)
    search_fields = ("sample__sample_code",)
    readonly_fields = ("decided_at",)
