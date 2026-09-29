from django.urls import path

from . import views

app_name = "catalogos"

urlpatterns = [
    path("tracto/", views.tracto_de_conductor, name="tracto_de_conductor"),
]
