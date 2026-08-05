from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Conductor, TarifaMaestra


@login_required
def opciones_tarifas(request):
    """Fragmento htmx: opciones del <select> de tarifas para un proveedor dado."""
    proveedor = request.GET.get("proveedor_select", "") or request.GET.get("proveedor", "")
    tarifas = TarifaMaestra.objects.filter(estado="Activa")
    if proveedor:
        tarifas = tarifas.filter(proveedor=proveedor)
    else:
        tarifas = tarifas.none()
    return render(request, "catalogos/_opciones_tarifa.html", {"tarifas": tarifas})


@login_required
def previsualizar_tarifa(request):
    """Fragmento htmx: resumen de la tarifa seleccionada (mandante, ruta, neto/IVA/total)."""
    tarifa_id = request.GET.get("tarifa_id")
    tarifa = TarifaMaestra.objects.filter(pk=tarifa_id).first() if tarifa_id else None
    return render(request, "catalogos/_previsualizacion_tarifa.html", {"tarifa": tarifa})


@login_required
def tracto_de_conductor(request):
    """Fragmento htmx: autocompleta el input de tracto según el conductor elegido."""
    nombre = request.GET.get("conductor_principal", "") or request.GET.get("conductor", "")
    tracto = ""
    if nombre:
        conductor = Conductor.objects.filter(nombre=nombre).first()
        tracto = conductor.tracto_patente or "" if conductor else ""
    return render(request, "catalogos/_tracto_valor.html", {"tracto": tracto})
