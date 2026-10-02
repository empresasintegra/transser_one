from django.contrib import admin

from .models import ComisionServicio, EventoServicio, ParadaServicio, Servicio


class ComisionInline(admin.TabularInline):
    model = ComisionServicio
    extra = 0


class ParadaInline(admin.TabularInline):
    model = ParadaServicio
    extra = 0


class EventoInline(admin.TabularInline):
    model = EventoServicio
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in EventoServicio._meta.fields if f.name not in ("id",)]


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "ruta", "estado", "tarifa", "fecha_carga", "creado_por")
    list_filter = ("estado", "tipo_servicio", "cliente")
    search_fields = (
        "numero", "cliente__razon_social", "ruta__comuna_origen__nombre", "ruta__comuna_destino__nombre",
    )
    list_select_related = ("cliente", "ruta__comuna_origen", "ruta__comuna_destino", "creado_por")
    inlines = [ComisionInline, ParadaInline, EventoInline]
    date_hierarchy = "fecha_carga"
    autocomplete_fields = ("cliente", "mandante", "local_destino", "ruta", "conductor_principal", "conductor_secundario", "tracto", "rampla")
    raw_id_fields = ("tarifa_ref",)
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(ParadaServicio)
class ParadaServicioAdmin(admin.ModelAdmin):
    list_display = ("servicio", "local", "es_valor_extra", "ruta", "tipo_tarifa", "valor", "creado_por", "creado_en")
    list_filter = ("es_valor_extra", "tipo_tarifa")
    search_fields = ("servicio__numero", "local__nombre", "observacion")
    raw_id_fields = ("servicio", "tarifa_ref")
    autocomplete_fields = ("local", "ruta")


@admin.register(ComisionServicio)
class ComisionServicioAdmin(admin.ModelAdmin):
    list_display = ("servicio", "conductor", "porcentaje", "motivo")
    search_fields = ("servicio__numero", "conductor__nombre", "motivo")
    raw_id_fields = ("servicio",)


@admin.register(EventoServicio)
class EventoServicioAdmin(admin.ModelAdmin):
    list_display = ("servicio", "tipo", "estado_anterior", "estado_nuevo", "actor", "creado_en")
    list_filter = ("tipo", "estado_nuevo")
    search_fields = ("servicio__numero", "actor__nombre", "motivo")
    raw_id_fields = ("servicio",)
    readonly_fields = ("creado_en",)
