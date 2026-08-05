from django.urls import path

from . import views

app_name = "operaciones"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("operaciones/", views.centro_operaciones, name="centro_operaciones"),
    path("operaciones/nuevo/", views.crear_servicio, name="crear_servicio"),
    path("operaciones/<int:servicio_id>/", views.servicio_detalle, name="servicio_detalle"),
    path("operaciones/<int:servicio_id>/estado/", views.cambiar_estado, name="cambiar_estado"),
    path("operaciones/<int:servicio_id>/rampla/", views.cambiar_rampla, name="cambiar_rampla"),
    path("operaciones/<int:servicio_id>/tarifa/", views.modificar_tarifa, name="modificar_tarifa"),
    path("operaciones/<int:servicio_id>/datos/", views.modificar_datos, name="modificar_datos"),
]
