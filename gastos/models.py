from decimal import Decimal

from django.conf import settings
from django.db import models

from maestros.models import CentroCosto, Proveedor
from operaciones.models import Servicio


class CategoriaGasto(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    grupo = models.CharField(max_length=60)
    nombre = models.CharField(max_length=100, unique=True)
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.PROTECT, blank=True, null=True, related_name="categorias_gasto")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["grupo", "nombre"]
        verbose_name = "categoría de gasto"
        verbose_name_plural = "categorías de gasto"

    def __str__(self):
        return f"{self.grupo} · {self.nombre}"


class GastoRuta(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        REVISADO = "Revisado", "Revisado"
        APROBADO = "Aprobado", "Aprobado"
        RECHAZADO = "Rechazado", "Rechazado"
        CONTABILIZADO = "Contabilizado", "Contabilizado"

    servicio = models.ForeignKey(Servicio, related_name="gastos", on_delete=models.CASCADE)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT)
    fecha = models.DateField()
    descripcion = models.CharField(max_length=250)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, blank=True, null=True, related_name="gastos")
    documento_tipo = models.CharField(max_length=50, blank=True, null=True)
    documento_numero = models.CharField(max_length=80, blank=True, null=True)
    monto_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    afecto_iva = models.BooleanField(default=True)
    tasa_iva = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quien_pago = models.CharField(max_length=50, default="Empresa")
    medio_pago = models.CharField(max_length=50, default="Transferencia")
    requiere_rendicion = models.BooleanField(default=False)
    reembolsable = models.BooleanField(default=False)
    evidencia = models.CharField(max_length=500, blank=True, null=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PENDIENTE)
    observacion = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gastos_creados")
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True, related_name="gastos_aprobados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def calcular_totales(self):
        neto = Decimal(self.monto_neto)
        tasa = Decimal(self.tasa_iva) if self.afecto_iva else Decimal("0")
        iva = (neto * tasa / Decimal("100")).quantize(Decimal("1"))
        self.iva = iva
        self.monto_total = neto + iva
