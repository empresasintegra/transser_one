from django.contrib import admin

from .models import CategoriaGasto, GastoRuta


@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "grupo", "nombre", "centro_costo", "activa")
    list_filter = ("grupo", "activa", "centro_costo")
    search_fields = ("codigo", "nombre")


@admin.register(GastoRuta)
class GastoRutaAdmin(admin.ModelAdmin):
    list_display = ("servicio", "categoria", "fecha", "monto_total", "estado", "creado_por", "aprobado_por")
    list_filter = ("estado", "categoria")
    search_fields = ("descripcion", "proveedor__nombre", "servicio__numero", "documento_numero")
    date_hierarchy = "fecha"
    raw_id_fields = ("servicio",)
    autocomplete_fields = ("proveedor",)
    readonly_fields = ("creado_en",)
    list_select_related = ("servicio", "categoria")
