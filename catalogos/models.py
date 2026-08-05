from decimal import Decimal

from django.db import models


class Conductor(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "Activo", "Activo"
        INACTIVO = "Inactivo", "Inactivo"

    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField(max_length=20, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    tracto_patente = models.CharField(max_length=20, blank=True, null=True)
    modelo_tracto = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.ACTIVO)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Tracto(models.Model):
    patente = models.CharField(max_length=20, unique=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    conductor_asignado = models.CharField(max_length=150, blank=True, null=True)
    rut_conductor = models.CharField(max_length=20, blank=True, null=True)
    estado = models.CharField(max_length=30, default="Disponible")
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["patente"]

    def __str__(self):
        return self.patente


class TarifaMaestra(models.Model):
    proveedor = models.CharField(max_length=150)
    mandante = models.CharField(max_length=150, blank=True, null=True)
    codigo_local = models.CharField(max_length=30, blank=True, null=True)
    region = models.CharField(max_length=30, blank=True, null=True)
    origen = models.CharField(max_length=150)
    destino = models.CharField(max_length=200)
    ruta = models.CharField(max_length=350)
    tipo_servicio = models.CharField(max_length=30)
    tarifa_neta = models.DecimalField(max_digits=14, decimal_places=2)
    tasa_iva = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    vigente_desde = models.DateField(blank=True, null=True)
    vigente_hasta = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=30, default="Activa")
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["destino", "tipo_servicio"]
        verbose_name = "tarifa maestra"
        verbose_name_plural = "tarifas maestras"

    def __str__(self):
        return f"{self.proveedor} · {self.ruta}"

    @property
    def iva(self):
        return (self.tarifa_neta * self.tasa_iva / Decimal("100")).quantize(Decimal("1"))

    @property
    def total(self):
        return self.tarifa_neta + self.iva
