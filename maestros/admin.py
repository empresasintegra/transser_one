from django.contrib import admin

from .models import (
    CentroCosto,
    Cliente,
    Comuna,
    FormaDePago,
    HorarioRecepcion,
    Local,
    Prioridad,
    Proveedor,
    Rampla,
    Region,
    Ruta,
    Tarifa,
    TipoRampla,
    TipoServicio,
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "region")
    list_filter = ("region",)
    search_fields = ("nombre",)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "contacto_nombre", "contacto_telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "rut")


@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(Prioridad)
class PrioridadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(TipoRampla)
class TipoRamplaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(FormaDePago)
class FormaDePagoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


class LocalInline(admin.TabularInline):
    model = Local
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "contacto_nombre", "contacto_telefono", "ejecutivo_comercial", "activo")
    list_filter = ("activo",)
    search_fields = ("razon_social", "rut")
    inlines = [LocalInline]


@admin.register(HorarioRecepcion)
class HorarioRecepcionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "codigo", "horario_recepcion", "comuna", "activo")
    list_filter = ("activo", "horario_recepcion", "comuna__region")
    search_fields = ("nombre", "codigo", "cliente__razon_social")
    readonly_fields = ("codigo",)


@admin.register(Rampla)
class RamplaAdmin(admin.ModelAdmin):
    list_display = ("patente", "tipo_rampla", "es_externa", "proveedor", "activa")
    list_filter = ("tipo_rampla", "es_externa", "activa")
    search_fields = ("patente",)


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ("comuna_origen", "comuna_destino", "kilometros", "activa")
    list_filter = ("activa",)
    search_fields = ("comuna_origen__nombre", "comuna_destino__nombre")


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ("cliente", "local", "ruta", "seco", "frio", "congelado", "unica", "activa")
    list_filter = ("activa",)
    search_fields = ("cliente__razon_social",)
