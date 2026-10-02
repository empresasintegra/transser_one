from decimal import Decimal

from django.conf import settings
from django.db import models

from catalogos.models import Conductor, Tracto
from maestros.models import Cliente, Local, Rampla, Ruta, Tarifa, TipoServicio

# Los 4 campos de maestros.Tarifa que pueden traer un valor cargado. Vive
# acá (no en views.py) para que tanto el <select> de "Nuevo Servicio" como
# el de ParadaServicio.tipo_tarifa usen la misma fuente — ver
# operaciones/views.py.
TIPOS_TARIFA = [
    ("seco", "Seco"),
    ("frio", "Frío"),
    ("congelado", "Congelado"),
    ("unica", "Única"),
]


class Servicio(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = "Programado", "Programado"
        CARGANDO = "Cargando", "Cargando"
        EN_RUTA = "En Ruta", "En Ruta"
        DESCARGANDO = "Descargando", "Descargando"
        FINALIZADO = "Finalizado", "Finalizado"

    TRANSICIONES = {
        Estado.PROGRAMADO: {Estado.CARGANDO},
        Estado.CARGANDO: {Estado.EN_RUTA},
        Estado.EN_RUTA: {Estado.DESCARGANDO},
        Estado.DESCARGANDO: {Estado.FINALIZADO},
        Estado.FINALIZADO: set(),
    }

    numero = models.CharField(max_length=30, unique=True, blank=True, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="servicios")
    mandante = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, blank=True, null=True, related_name="servicios_como_mandante",
        help_text="Cliente final cuando el servicio se contrata a través de un intermediario.",
    )
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, blank=True, null=True, related_name="servicios")
    # FK a maestros.Tarifa (no a catalogos.TarifaMaestra, que quedó sin uso
    # una vez que Nuevo Servicio pasó a tomar los datos de maestros): deja
    # trazabilidad de qué fila de tarifa se usó, aunque el valor real
    # cobrado queda fijo en el campo `tarifa` de abajo (foto del momento).
    tarifa_ref = models.ForeignKey(Tarifa, null=True, blank=True, on_delete=models.SET_NULL, related_name="servicios")
    local_destino = models.ForeignKey(Local, null=True, blank=True, on_delete=models.SET_NULL, related_name="servicios_destino")
    # Origen y destino salen de la ruta (comuna origen / comuna destino);
    # antes se copiaban como texto y podían quedar desfasados de ella.
    ruta = models.ForeignKey(Ruta, on_delete=models.PROTECT, related_name="servicios")
    fecha_carga = models.DateField()
    fecha_entrega_estimada = models.DateField(null=True, blank=True)
    tipo_carga = models.CharField(max_length=20, choices=TIPOS_TARIFA, blank=True, null=True)
    conductor_principal = models.ForeignKey(
        Conductor, on_delete=models.SET_NULL, blank=True, null=True, related_name="servicios_como_principal",
    )
    conductor_secundario = models.ForeignKey(
        Conductor, on_delete=models.SET_NULL, blank=True, null=True, related_name="servicios_como_secundario",
    )
    tracto = models.ForeignKey(Tracto, on_delete=models.SET_NULL, blank=True, null=True, related_name="servicios")
    rampla = models.ForeignKey(Rampla, on_delete=models.SET_NULL, blank=True, null=True, related_name="servicios")
    tarifa = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tasa_iva = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_factura = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PROGRAMADO)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="servicios_creados")
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.numero or f"Servicio #{self.pk}"

    @property
    def origen(self):
        return str(self.ruta.comuna_origen)

    @property
    def destino(self):
        return str(self.ruta.comuna_destino)

    @property
    def codigo_local(self):
        return self.local_destino.codigo if self.local_destino_id else None

    def calcular_iva_total(self):
        neto = Decimal(self.tarifa)
        tasa = Decimal(self.tasa_iva)
        iva = (neto * tasa / Decimal("100")).quantize(Decimal("1"))
        self.iva = iva
        self.total_factura = neto + iva


class EventoServicio(models.Model):
    servicio = models.ForeignKey(Servicio, related_name="eventos", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    estado_anterior = models.CharField(max_length=30, blank=True, null=True)
    estado_nuevo = models.CharField(max_length=30, blank=True, null=True)
    rampla_anterior = models.ForeignKey(Rampla, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    rampla_nueva = models.ForeignKey(Rampla, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_realizados")
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True, related_name="eventos_autorizados",
    )
    motivo = models.TextField(blank=True, null=True)
    evidencia_foto = models.CharField(max_length=500, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class ComisionServicio(models.Model):
    servicio = models.ForeignKey(Servicio, related_name="comisiones", on_delete=models.CASCADE)
    conductor = models.ForeignKey(Conductor, on_delete=models.PROTECT, related_name="comisiones")
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    motivo = models.CharField(max_length=250, blank=True, null=True)


class ParadaServicio(models.Model):
    """Una parada adicional dentro del mismo viaje — ej. un camión que en
    la ruta a Iquique también pasa a dejar algo a Alto Hospicio.

    Dos modalidades (ver `es_valor_extra`):
    - Normal: local + ruta + tipo de carga, igual que el servicio
      principal — el valor se resuelve solo desde `maestros.Tarifa`.
    - Valor extra: un cobro puntual en ese local (ej. un peaje especial,
      un cargo de manipulación) que no sale del tarifario, se escribe a
      mano.
    """

    servicio = models.ForeignKey(Servicio, related_name="paradas", on_delete=models.CASCADE)
    local = models.ForeignKey(Local, on_delete=models.PROTECT, related_name="paradas_servicio")
    es_valor_extra = models.BooleanField(
        "valor extra", default=False,
        help_text="Un cobro adicional en este local, no una entrega con tarifa de ruta.",
    )
    ruta = models.ForeignKey(Ruta, on_delete=models.PROTECT, blank=True, null=True, related_name="paradas_servicio")
    tipo_tarifa = models.CharField(max_length=20, choices=TIPOS_TARIFA, blank=True, null=True)
    tarifa_ref = models.ForeignKey(
        Tarifa, on_delete=models.SET_NULL, blank=True, null=True, related_name="paradas_servicio",
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacion = models.CharField(max_length=250, blank=True, null=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="paradas_creadas")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "parada de servicio"
        verbose_name_plural = "paradas de servicio"

    def __str__(self):
        return f"{self.local} · ${self.valor}"
