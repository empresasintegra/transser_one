from django.contrib import admin

from .models import Conductor, TarifaMaestra, Tracto


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "tracto_patente", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "rut")


@admin.register(Tracto)
class TractoAdmin(admin.ModelAdmin):
    list_display = ("patente", "modelo", "conductor_asignado", "estado")
    list_filter = ("estado",)
    search_fields = ("patente", "conductor_asignado")


@admin.register(TarifaMaestra)
class TarifaMaestraAdmin(admin.ModelAdmin):
    list_display = ("proveedor", "ruta", "tipo_servicio", "tarifa_neta", "estado")
    list_filter = ("proveedor", "tipo_servicio", "estado")
    search_fields = ("proveedor", "ruta", "destino", "codigo_local")
