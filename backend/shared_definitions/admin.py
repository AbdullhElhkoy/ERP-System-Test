from django.contrib import admin
from .models import QualityGrade


@admin.register(QualityGrade)
class QualityGradeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")