from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Tracto


@login_required
def tracto_de_conductor(request):
    """Fragmento htmx: muestra el tracto asignado al conductor elegido (solo informativo;
    al crear el servicio el tracto se vuelve a resolver en el servidor)."""
    conductor_id = request.GET.get("conductor_principal") or request.GET.get("conductor")
    tracto = Tracto.objects.filter(conductor_id=conductor_id).first() if conductor_id else None
    return render(request, "catalogos/_tracto_valor.html", {"tracto": tracto.patente if tracto else ""})
