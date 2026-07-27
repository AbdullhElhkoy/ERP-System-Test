from django.conf import settings
from django.db import models
from plants.models import OrgPosition


class UserProfile(models.Model):
    """
    الربط بين مستخدم Django والمنصب التنظيمي بتاعه (OrgPosition).
    ده اللي هيحدد صلاحيات المستخدم (يشوف كل حاجة ولا Phase 1 بس).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    org_position = models.ForeignKey(
        OrgPosition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        help_text="المنصب التنظيمي بتاع المستخدم (لو موجود)",
    )

    class Meta:
        verbose_name = "User Profile (ملف المستخدم)"
        verbose_name_plural = "User Profiles (ملفات المستخدمين)"

    def __str__(self):
        return f"{self.user.username} - {self.org_position or 'بدون منصب'}"