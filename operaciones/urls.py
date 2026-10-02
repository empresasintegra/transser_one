from django.urls import path

from . import views

app_name = "operaciones"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("operaciones/", views.centro_operaciones, name="centro_operaciones"),
    path("operaciones/nuevo/", views.crear_servicio, name="crear_servicio"),
    path("operaciones/nuevo/rutas/", views.opciones_rutas_cliente, name="opciones_rutas_cliente"),
    path("operaciones/nuevo/locales/", views.opciones_locales_cliente_servicio, name="opciones_locales_cliente_servicio"),
    path("operaciones/nuevo/tarifa/", views.previsualizar_tarifa_servicio, name="previsualizar_tarifa_servicio"),
    path("operaciones/reportes/", views.reportes, name="reportes"),
    path("operaciones/reportes/excel/", views.reportes_excel, name="reportes_excel"),
    path("operaciones/<int:servicio_id>/", views.servicio_detalle, name="servicio_detalle"),
    path("operaciones/<int:servicio_id>/guia/", views.guia_despacho_pdf, name="guia_despacho_pdf"),
    path("operaciones/<int:servicio_id>/estado/", views.cambiar_estado, name="cambiar_estado"),
    path("operaciones/<int:servicio_id>/rampla/", views.cambiar_rampla, name="cambiar_rampla"),
    path("operaciones/<int:servicio_id>/tarifa/", views.modificar_tarifa, name="modificar_tarifa"),
    path("operaciones/<int:servicio_id>/datos/", views.modificar_datos, name="modificar_datos"),
    path("operaciones/<int:servicio_id>/paradas/", views.crear_parada, name="crear_parada"),
    path("paradas/<int:parada_id>/eliminar/", views.eliminar_parada, name="eliminar_parada"),
]
