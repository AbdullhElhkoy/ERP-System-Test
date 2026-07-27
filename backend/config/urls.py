"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include  # تم إضافة include هنا

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/dcp-reaction/', include('dcp_reaction.urls')), # تم إضافة مسار الـ API
]