from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Conductor


@login_required
def tracto_de_conductor(request):
    """Fragmento htmx: autocompleta el input de tracto según el conductor elegido."""
    nombre = request.GET.get("conductor_principal", "") or request.GET.get("conductor", "")
    tracto = ""
    if nombre:
        conductor = Conductor.objects.filter(nombre=nombre).first()
        tracto = conductor.tracto_patente or "" if conductor else ""
    return render(request, "catalogos/_tracto_valor.html", {"tracto": tracto})
