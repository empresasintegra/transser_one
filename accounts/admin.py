from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ("email", "nombre", "roles", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "groups")
    search_fields = ("email", "nombre")
    ordering = ("nombre",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre",)}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "creado_en")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nombre", "password1", "password2", "is_active", "is_staff", "groups"),
        }),
    )
    readonly_fields = ("creado_en",)

    @admin.display(description="Roles")
    def roles(self, obj):
        return ", ".join(g.name for g in obj.groups.all()) or "—"
