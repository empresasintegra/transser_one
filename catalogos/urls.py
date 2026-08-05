from django.urls import path

from . import views

app_name = "catalogos"

urlpatterns = [
    path("tarifas/", views.opciones_tarifas, name="opciones_tarifas"),
    path("previsualizar/", views.previsualizar_tarifa, name="previsualizar_tarifa"),
    path("tracto/", views.tracto_de_conductor, name="tracto_de_conductor"),
]
