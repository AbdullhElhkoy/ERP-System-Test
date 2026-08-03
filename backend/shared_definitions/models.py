from django.db import models


class QualityGrade(models.Model):
    """
    التصنيف النهائي المشترك بين كل المصانع (شركة واحدة، جدول واحد بس)
    """
    EXPORT = "export"
    LOCAL = "local"
    NON_CONFORMING = "non_conforming"
    CODE_CHOICES = [
        (EXPORT, "تصدير"),
        (LOCAL, "محلي"),
        (NON_CONFORMING, "غير مطابق"),
    ]

    code = models.CharField(max_length=20, choices=CODE_CHOICES, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "quality_grades"

    def __str__(self):
        return self.get_code_display()