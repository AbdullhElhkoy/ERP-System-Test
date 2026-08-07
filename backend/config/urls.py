from django.contrib import admin
from django.urls import path, include
import config.admin  # noqa: F401  - بيفعّل تقسيم صفحة الأدمن بتاعة factory

urlpatterns = [
    path('admin/', admin.site.urls),
]