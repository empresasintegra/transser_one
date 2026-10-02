from django.contrib import admin

from .models import Conductor, Tracto


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "proveedor", "tipo_contrato", "estado")
    list_filter = ("estado", "tipo_contrato", "proveedor")
    search_fields = ("nombre", "rut", "proveedor__nombre")
    autocomplete_fields = ("proveedor",)
    list_select_related = ("proveedor",)


@admin.register(Tracto)
class TractoAdmin(admin.ModelAdmin):
    list_display = ("patente", "marca", "modelo", "conductor", "tag", "estado")
    list_filter = ("estado", "marca")
    search_fields = ("patente", "conductor__nombre", "tag")
    autocomplete_fields = ("conductor",)
    list_select_related = ("conductor",)
