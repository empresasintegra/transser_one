from django.contrib import admin

from .models import ComisionServicio, EventoServicio, Servicio


class ComisionInline(admin.TabularInline):
    model = ComisionServicio
    extra = 0


class EventoInline(admin.TabularInline):
    model = EventoServicio
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in EventoServicio._meta.fields if f.name not in ("id",)]


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "origen", "destino", "estado", "tarifa", "fecha_carga", "creado_por")
    list_filter = ("estado", "tipo_servicio")
    search_fields = ("numero", "cliente", "origen", "destino")
    inlines = [ComisionInline, EventoInline]
