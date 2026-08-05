from django.urls import path

from . import views

app_name = "gastos"

urlpatterns = [
    path("servicio/<int:servicio_id>/nuevo/", views.crear_gasto, name="crear_gasto"),
    path("<int:gasto_id>/estado/", views.cambiar_estado_gasto, name="cambiar_estado_gasto"),
    path("<int:gasto_id>/eliminar/", views.eliminar_gasto, name="eliminar_gasto"),
]
