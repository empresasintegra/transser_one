from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import rol_requerido
from operaciones.models import Servicio

from .models import CategoriaGasto, GastoRuta

ROLES_APROBADORES_GASTO = ("Administrador", "Gerencia")


@login_required
@require_POST
def crear_gasto(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    categoria = get_object_or_404(CategoriaGasto, pk=request.POST.get("categoria_id"), activa=True)

    descripcion = request.POST.get("descripcion", "").strip()
    fecha = parse_date(request.POST.get("fecha") or "")
    try:
        monto_neto = Decimal(request.POST.get("monto_neto") or "0")
    except Exception:
        monto_neto = Decimal("0")

    if monto_neto <= 0 or not descripcion or not fecha:
        messages.error(request, "Descripción, fecha y monto neto son obligatorios.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    afecto_iva = request.POST.get("afecto_iva") == "on"
    gasto = GastoRuta(
        servicio=servicio,
        categoria=categoria,
        fecha=fecha,
        descripcion=descripcion,
        proveedor=request.POST.get("proveedor") or None,
        documento_tipo=request.POST.get("documento_tipo") or None,
        documento_numero=request.POST.get("documento_numero") or None,
        monto_neto=monto_neto,
        afecto_iva=afecto_iva,
        tasa_iva=Decimal("19") if afecto_iva else Decimal("0"),
        quien_pago=request.POST.get("quien_pago", "Empresa"),
        medio_pago=request.POST.get("medio_pago", "Transferencia"),
        requiere_rendicion=request.POST.get("requiere_rendicion") == "on",
        reembolsable=request.POST.get("reembolsable") == "on",
        evidencia=request.POST.get("evidencia") or None,
        observacion=request.POST.get("observacion") or None,
        creado_por=request.user.nombre,
    )
    gasto.calcular_totales()
    gasto.save()
    messages.success(request, "Gasto registrado.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)


@rol_requerido(*ROLES_APROBADORES_GASTO)
@require_POST
def cambiar_estado_gasto(request, gasto_id):
    gasto = get_object_or_404(GastoRuta, pk=gasto_id)
    nuevo_estado = request.POST.get("estado")
    if nuevo_estado not in GastoRuta.Estado.values:
        messages.error(request, "Estado de gasto no permitido.")
        return redirect("operaciones:servicio_detalle", servicio_id=gasto.servicio_id)

    gasto.estado = nuevo_estado
    gasto.aprobado_por = request.user.nombre if nuevo_estado in {GastoRuta.Estado.APROBADO, GastoRuta.Estado.CONTABILIZADO} else None
    gasto.save(update_fields=["estado", "aprobado_por"])
    messages.success(request, f"Gasto marcado como {nuevo_estado}.")
    return redirect("operaciones:servicio_detalle", servicio_id=gasto.servicio_id)


@login_required
@require_POST
def eliminar_gasto(request, gasto_id):
    gasto = get_object_or_404(GastoRuta, pk=gasto_id)
    if gasto.estado in {GastoRuta.Estado.APROBADO, GastoRuta.Estado.CONTABILIZADO}:
        messages.error(request, "No se puede eliminar un gasto aprobado o contabilizado.")
        return redirect("operaciones:servicio_detalle", servicio_id=gasto.servicio_id)
    servicio_id = gasto.servicio_id
    gasto.delete()
    messages.success(request, "Gasto eliminado.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio_id)
