from decimal import Decimal

from django.db import models

from maestros.models import Tarifa


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
    cliente = models.CharField(max_length=150)
    mandante = models.CharField(max_length=150, blank=True, null=True)
    codigo_local = models.CharField(max_length=30, blank=True, null=True)
    tipo_servicio = models.CharField(max_length=30, blank=True, null=True)
    # FK a maestros.Tarifa (no a catalogos.TarifaMaestra, que quedó sin uso
    # una vez que Nuevo Servicio pasó a tomar los datos de maestros): deja
    # trazabilidad de qué fila de tarifa se usó, aunque el valor real
    # cobrado queda fijo en el campo `tarifa` de abajo (foto del momento).
    tarifa_ref = models.ForeignKey(Tarifa, null=True, blank=True, on_delete=models.SET_NULL, related_name="servicios")
    origen = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    fecha_carga = models.DateField()
    fecha_entrega_estimada = models.DateField(null=True, blank=True)
    tipo_carga = models.CharField(max_length=100, blank=True, null=True)
    conductor_principal = models.CharField(max_length=150, blank=True, null=True)
    conductor_secundario = models.CharField(max_length=150, blank=True, null=True)
    tracto = models.CharField(max_length=20, blank=True, null=True)
    rampla = models.CharField(max_length=20, blank=True, null=True)
    tarifa = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tasa_iva = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_factura = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PROGRAMADO)
    creado_por = models.CharField(max_length=150)
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.numero or f"Servicio #{self.pk}"

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
    rampla_anterior = models.CharField(max_length=20, blank=True, null=True)
    rampla_nueva = models.CharField(max_length=20, blank=True, null=True)
    actor = models.CharField(max_length=150)
    autorizado_por = models.CharField(max_length=150, blank=True, null=True)
    motivo = models.TextField(blank=True, null=True)
    evidencia_foto = models.CharField(max_length=500, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class ComisionServicio(models.Model):
    servicio = models.ForeignKey(Servicio, related_name="comisiones", on_delete=models.CASCADE)
    conductor = models.CharField(max_length=150)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    motivo = models.CharField(max_length=250, blank=True, null=True)
