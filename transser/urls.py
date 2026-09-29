from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("operaciones.urls")),
    path("gastos/", include("gastos.urls")),
    path("catalogos/", include("catalogos.urls")),
    path("maestros/", include("maestros.urls")),
]
