from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import rol_requerido
from catalogos.models import Conductor, TarifaMaestra
from gastos.models import CategoriaGasto, GastoRuta

from .models import ComisionServicio, EventoServicio, Servicio

ROL_CREADOR_SERVICIO = "Operaciones"
ROLES_AUTORIZADORES_CAMBIO = ("Administrador", "Gerencia")
ROL_MODIFICADOR_TARIFA = "Administrador"


@login_required
def dashboard(request):
    servicios = Servicio.objects.all()
    hoy = date.today()

    servicios_mes = servicios.filter(fecha_carga__year=hoy.year, fecha_carga__month=hoy.month)
    ventas_hoy = sum((s.tarifa for s in servicios.filter(fecha_carga=hoy)), Decimal("0"))
    ventas_mes = sum((s.tarifa for s in servicios_mes), Decimal("0"))
    facturacion_mes = sum((s.total_factura for s in servicios_mes), Decimal("0"))
    activos = servicios.exclude(estado=Servicio.Estado.FINALIZADO)
    servicios_mes_count = servicios_mes.count()
    ticket_promedio = (ventas_mes / servicios_mes_count) if servicios_mes_count else Decimal("0")

    contexto = {
        "ventas_hoy": ventas_hoy,
        "ventas_mes": ventas_mes,
        "facturacion_mes": facturacion_mes,
        "servicios_mes_count": servicios_mes_count,
        "activos_count": activos.count(),
        "finalizados_mes": servicios_mes.filter(estado=Servicio.Estado.FINALIZADO).count(),
        "clientes_mes": servicios_mes.values("cliente").distinct().count(),
        "ticket_promedio": ticket_promedio,
        "en_ruta": servicios.filter(estado=Servicio.Estado.EN_RUTA).count(),
        "distribucion": {etiqueta: servicios.filter(estado=valor).count() for valor, etiqueta in Servicio.Estado.choices},
        "recientes": servicios.order_by("-fecha_carga", "-id")[:8],
    }
    return render(request, "operaciones/dashboard.html", contexto)


@login_required
def centro_operaciones(request):
    servicios = Servicio.objects.all()
    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "")

    if filtro_estado:
        servicios = servicios.filter(estado=filtro_estado)
    if busqueda:
        servicios = servicios.filter(
            Q(numero__icontains=busqueda)
            | Q(cliente__icontains=busqueda)
            | Q(origen__icontains=busqueda)
            | Q(destino__icontains=busqueda)
            | Q(conductor_principal__icontains=busqueda)
            | Q(tracto__icontains=busqueda)
            | Q(rampla__icontains=busqueda)
        )

    resumen = [
        (valor, etiqueta, Servicio.objects.filter(estado=valor).count())
        for valor, etiqueta in Servicio.Estado.choices
    ]

    contexto = {
        "servicios": servicios,
        "estados": Servicio.Estado.choices,
        "resumen": resumen,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
    }
    return render(request, "operaciones/centro_operaciones.html", contexto)


@login_required
def servicio_detalle(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    gastos = servicio.gastos.select_related("categoria").all()
    gastos_validos = gastos.exclude(estado=GastoRuta.Estado.RECHAZADO)
    gastos_netos = sum((g.monto_neto for g in gastos_validos), Decimal("0"))
    utilidad = servicio.tarifa - gastos_netos
    margen = (utilidad / servicio.tarifa * 100) if servicio.tarifa else Decimal("0")
    siguiente_estado = next(iter(Servicio.TRANSICIONES.get(servicio.estado, [])), None)

    contexto = {
        "servicio": servicio,
        "gastos": gastos,
        "categorias": CategoriaGasto.objects.filter(activa=True),
        "gastos_netos": gastos_netos,
        "utilidad": utilidad,
        "margen": margen,
        "gastos_pendientes": gastos.filter(estado__in=[GastoRuta.Estado.PENDIENTE, GastoRuta.Estado.REVISADO]).count(),
        "siguiente_estado": siguiente_estado,
    }
    return render(request, "operaciones/detalle.html", contexto)


@rol_requerido(ROL_CREADOR_SERVICIO)
def crear_servicio(request):
    if request.method == "POST":
        tarifa_id = request.POST.get("tarifa_id") or None
        tarifa_obj = None

        cliente = request.POST.get("proveedor_select", "").strip()
        origen = ""
        destino = ""
        mandante = None
        codigo_local = None
        tipo_servicio = None
        tarifa = Decimal("0")
        tasa_iva = Decimal("19")

        fecha_carga = parse_date(request.POST.get("fecha_carga") or "")

        if not cliente or not fecha_carga:
            messages.error(request, "Completa el cliente y la fecha de carga.")
            return redirect("operaciones:crear_servicio")

        if tarifa_id:
            tarifa_obj = get_object_or_404(TarifaMaestra, pk=tarifa_id, estado="Activa")
            cliente = tarifa_obj.proveedor
            mandante = tarifa_obj.mandante
            codigo_local = tarifa_obj.codigo_local
            tipo_servicio = tarifa_obj.tipo_servicio
            origen = tarifa_obj.origen
            destino = tarifa_obj.destino
            tarifa = tarifa_obj.tarifa_neta
            tasa_iva = tarifa_obj.tasa_iva
        else:
            messages.error(request, "Selecciona una ruta/tarifa para el servicio.")
            return redirect("operaciones:crear_servicio")

        servicio = Servicio(
            cliente=cliente,
            mandante=mandante,
            codigo_local=codigo_local,
            tipo_servicio=tipo_servicio,
            tarifa_maestra=tarifa_obj,
            origen=origen,
            destino=destino,
            fecha_carga=fecha_carga,
            fecha_entrega_estimada=parse_date(request.POST.get("fecha_entrega_estimada") or ""),
            tipo_carga=request.POST.get("tipo_carga") or None,
            conductor_principal=request.POST.get("conductor_principal") or None,
            tracto=request.POST.get("tracto") or None,
            rampla=request.POST.get("rampla") or None,
            tarifa=tarifa,
            tasa_iva=tasa_iva,
            observaciones=request.POST.get("observaciones") or None,
            creado_por=request.user.nombre,
        )
        servicio.calcular_iva_total()
        servicio.save()
        servicio.numero = f"TS-{servicio.fecha_carga.year}-{servicio.id:06d}"
        servicio.save(update_fields=["numero"])

        EventoServicio.objects.create(
            servicio=servicio,
            tipo="CREACION",
            estado_nuevo=Servicio.Estado.PROGRAMADO,
            actor=request.user.nombre,
            motivo="Creación inicial del servicio.",
        )
        if servicio.conductor_principal:
            ComisionServicio.objects.create(
                servicio=servicio,
                conductor=servicio.conductor_principal,
                porcentaje=Decimal("100.00"),
                motivo="Conductor principal del servicio.",
            )

        messages.success(request, f"Servicio {servicio.numero} creado correctamente.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    contexto = {
        "proveedores": TarifaMaestra.objects.filter(estado="Activa").values_list("proveedor", flat=True).distinct().order_by("proveedor"),
        "conductores": Conductor.objects.filter(estado=Conductor.Estado.ACTIVO),
    }
    return render(request, "operaciones/servicio_form.html", contexto)


@login_required
@require_POST
def cambiar_estado(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    nuevo_estado = request.POST.get("nuevo_estado", "").strip()
    evidencia_foto = request.POST.get("evidencia_foto") or None
    motivo = request.POST.get("motivo") or f"Avance operacional a {nuevo_estado}"

    permitidos = Servicio.TRANSICIONES.get(servicio.estado, set())
    if nuevo_estado not in permitidos:
        messages.error(request, f"No se puede pasar de '{servicio.estado}' a '{nuevo_estado}'.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    if nuevo_estado in {Servicio.Estado.EN_RUTA, Servicio.Estado.FINALIZADO} and not evidencia_foto:
        messages.error(request, f"Para pasar a '{nuevo_estado}' es obligatoria una fotografía.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    estado_anterior = servicio.estado
    servicio.estado = nuevo_estado
    servicio.save(update_fields=["estado", "actualizado_en"])
    EventoServicio.objects.create(
        servicio=servicio,
        tipo="CAMBIO_ESTADO",
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        actor=request.user.nombre,
        motivo=motivo,
        evidencia_foto=evidencia_foto,
    )
    messages.success(request, f"Servicio avanzado a {nuevo_estado}.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)


@login_required
@require_POST
def cambiar_rampla(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    if servicio.estado not in {Servicio.Estado.EN_RUTA, Servicio.Estado.DESCARGANDO}:
        messages.error(request, "El cambio de rampla solo se permite En Ruta o Descargando.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    rampla_nueva = request.POST.get("rampla_nueva", "").strip()
    conductor_secundario = request.POST.get("conductor_secundario", "").strip()
    motivo = request.POST.get("motivo", "").strip()
    if not rampla_nueva or not conductor_secundario or len(motivo) < 3:
        messages.error(request, "Rampla, conductor secundario y motivo son obligatorios.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    rampla_anterior = servicio.rampla
    servicio.rampla = rampla_nueva
    servicio.conductor_secundario = conductor_secundario
    servicio.save(update_fields=["rampla", "conductor_secundario", "actualizado_en"])

    servicio.comisiones.all().delete()
    if servicio.conductor_principal:
        ComisionServicio.objects.create(
            servicio=servicio, conductor=servicio.conductor_principal,
            porcentaje=Decimal("50.00"), motivo="Reparto por reemplazo de rampla durante el viaje.",
        )
    ComisionServicio.objects.create(
        servicio=servicio, conductor=conductor_secundario,
        porcentaje=Decimal("50.00"), motivo="Reparto por reemplazo de rampla durante el viaje.",
    )

    EventoServicio.objects.create(
        servicio=servicio, tipo="CAMBIO_RAMPLA", rampla_anterior=rampla_anterior,
        rampla_nueva=rampla_nueva, actor=request.user.nombre, motivo=motivo,
    )
    messages.success(request, "Rampla actualizada.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)


@rol_requerido(ROL_MODIFICADOR_TARIFA)
@require_POST
def modificar_tarifa(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    motivo = request.POST.get("motivo", "").strip()
    try:
        tarifa_nueva = Decimal(request.POST.get("tarifa_nueva", "0"))
    except Exception:
        tarifa_nueva = Decimal("0")

    if tarifa_nueva <= 0 or len(motivo) < 3:
        messages.error(request, "Tarifa y motivo son obligatorios.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    tarifa_anterior = servicio.tarifa
    servicio.tarifa = tarifa_nueva
    servicio.calcular_iva_total()
    servicio.save(update_fields=["tarifa", "iva", "total_factura", "actualizado_en"])
    EventoServicio.objects.create(
        servicio=servicio, tipo="CAMBIO_TARIFA", actor=request.user.nombre,
        motivo=f"{motivo} Tarifa anterior: {tarifa_anterior}. Tarifa nueva: {tarifa_nueva}.",
    )
    messages.success(request, "Tarifa actualizada.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)


@rol_requerido(*ROLES_AUTORIZADORES_CAMBIO)
@require_POST
def modificar_datos(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    motivo = request.POST.get("motivo", "").strip()
    if len(motivo) < 3:
        messages.error(request, "El motivo es obligatorio.")
        return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)

    for campo in ("origen", "destino"):
        valor = request.POST.get(campo)
        if valor:
            setattr(servicio, campo, valor)
    for campo in ("fecha_carga", "fecha_entrega_estimada"):
        valor = parse_date(request.POST.get(campo) or "")
        if valor:
            setattr(servicio, campo, valor)
    servicio.save()

    EventoServicio.objects.create(
        servicio=servicio, tipo="CAMBIO_DATOS", actor=request.user.nombre,
        autorizado_por=request.user.nombre, motivo=motivo,
    )
    messages.success(request, "Datos del servicio actualizados.")
    return redirect("operaciones:servicio_detalle", servicio_id=servicio.id)
