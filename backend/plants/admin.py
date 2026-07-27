from django.contrib import admin
from .models import Plant, Department, Role, OrgPosition

admin.site.register(Plant)
admin.site.register(Department)
admin.site.register(Role)
admin.site.register(OrgPosition)