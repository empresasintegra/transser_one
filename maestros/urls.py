from django.urls import path

from . import views

app_name = "maestros"

urlpatterns = [
    path("", views.index, name="index"),
    path("fragmentos/locales-de-cliente/", views.locales_de_cliente, name="locales_de_cliente"),
    path("<slug:slug>/", views.lista, name="lista"),
    path("<slug:slug>/nuevo/", views.crear, name="crear"),
    path("<slug:slug>/<int:pk>/editar/", views.editar, name="editar"),
    path("<slug:slug>/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]
