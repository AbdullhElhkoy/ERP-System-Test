from django.contrib import admin
from django import forms
from django.template.response import TemplateResponse
from django.urls import path

from plants.models import Role
from .models import Screen, ScreenColumn, ColumnPermission


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(ScreenColumn)
class ScreenColumnAdmin(admin.ModelAdmin):
    list_display = ("screen", "code", "label", "order")
    list_filter = ("screen",)
    search_fields = ("code", "label")


@admin.register(ColumnPermission)
class ColumnPermissionAdmin(admin.ModelAdmin):
    list_display = ("column", "role", "level")
    list_filter = ("column__screen", "role", "level")
    search_fields = ("column__code", "column__label", "role__role_name")


# ---------------------------------------------------------------------------
# Permission Matrix — custom admin view
# ---------------------------------------------------------------------------

class ColumnPermissionInlineForm(forms.ModelForm):
    class Meta:
        model = ColumnPermission
        fields = "__all__"


class PermissionMatrixAdmin(admin.ModelAdmin):
    """Custom admin view showing a matrix of ScreenColumns × Roles."""

    def get_urls(self):
        custom = [
            path("matrix/", self.admin_site.admin_view(self.matrix_view), name="custom_permissions_matrix"),
        ]
        return custom + super().get_urls()

    def matrix_view(self, request):
        screen_id = request.GET.get("screen")
        screens = Screen.objects.prefetch_related("columns").all()
        roles = Role.objects.all()

        columns = []
        matrix = {}
        selected_screen = None

        if screen_id:
            selected_screen = Screen.objects.filter(pk=screen_id).first()
            if selected_screen:
                columns = selected_screen.columns.all().order_by("order")
                perms = ColumnPermission.objects.filter(
                    column__screen=selected_screen
                ).select_related("role")
                for p in perms:
                    matrix[(p.column_id, p.role_id)] = p.level

        if request.method == "POST" and selected_screen:
            for col in columns:
                for role in roles:
                    key = f"perm_{col.id}_{role.id}"
                    level = request.POST.get(key, ColumnPermission.LEVEL_HIDDEN)
                    if level in dict(ColumnPermission.LEVEL_CHOICES):
                        ColumnPermission.objects.update_or_create(
                            column=col,
                            role=role,
                            defaults={"level": level},
                        )
            from django.contrib import messages
            messages.success(request, f"Permissions saved for {selected_screen.name}.")
            return self.changelist_view(request)

        context = {
            **self.admin_site.each_context(request),
            "title": "Permission Matrix",
            "screens": screens,
            "selected_screen": selected_screen,
            "columns": columns,
            "roles": roles,
            "matrix": matrix,
            "level_choices": ColumnPermission.LEVEL_CHOICES,
        }
        return TemplateResponse(request, "admin/permission_matrix.html", context)


# Register the matrix view
admin.site.register(Screen, ScreenAdmin)
