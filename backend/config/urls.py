from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

import config.admin  # noqa: F401  - بيفعّل تقسيم صفحة الأدمن بتاعة factory

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('warehousing/', include('warehousing.urls')),
    path('factory/', include('factory.urls')),
    path('hr/', include('hr.urls')),
    path('it/', include('it.urls')),
]
