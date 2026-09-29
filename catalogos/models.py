from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Conductor(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "Activo", "Activo"
        INACTIVO = "Inactivo", "Inactivo"

    class TipoContrato(models.TextChoices):
        INDEFINIDO = "Indefinido", "Indefinido"
        PLAZO_FIJO = "Plazo Fijo", "Plazo Fijo"
        POR_OBRA_FAENA = "Por Obra o Faena", "Por Obra o Faena"
        HONORARIOS = "Honorarios", "Honorarios"

    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField(max_length=20, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    tracto_patente = models.CharField(max_length=20, blank=True, null=True)
    modelo_tracto = models.CharField(max_length=100, blank=True, null=True)
    # Agregados tras revisar el Excel real de la empresa (hoja "Transser"):
    direccion = models.CharField("dirección / ciudad", max_length=150, blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    # Choice fijo (no tabla aparte): los tipos de contrato son un catálogo
    # cerrado del Código del Trabajo, no algo que el usuario necesite editar.
    tipo_contrato = models.CharField(max_length=30, choices=TipoContrato.choices, blank=True, null=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.ACTIVO)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Tracto(models.Model):
    patente = models.CharField(max_length=20, unique=True)
    marca = models.CharField(max_length=60, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    tipo_camion = models.CharField(max_length=60, blank=True, null=True, help_text="Ej: Tracto Blanco, Tracto Rojo, Chasis.")
    # OneToOne (no ForeignKey): un conductor no puede manejar dos tractos a
    # la vez, así que la base de datos lo impide directamente en vez de
    # confiar solo en que el formulario filtre bien las opciones.
    conductor = models.OneToOneField(
        Conductor, related_name="tracto", on_delete=models.SET_NULL, blank=True, null=True,
        help_text="Conductor asignado a este tracto. Cada conductor puede manejar un solo tracto.",
    )
    # Agregados tras revisar el Excel real de la empresa (hoja "Transser"):
    tag = models.CharField("TAG", max_length=60, blank=True, null=True, help_text="Dispositivo de telepeaje.")
    tarjeta_combustible = models.CharField(max_length=60, blank=True, null=True, help_text="Ej: Shell Card, Aramco.")
    proveedor_gps = models.CharField(max_length=60, blank=True, null=True)
    estado = models.CharField(max_length=30, default="Disponible")
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["patente"]

    def __str__(self):
        return self.patente


@receiver(post_save, sender=Tracto)
def _sincronizar_conductor_tracto(sender, instance, **kwargs):
    """Mantiene sincronizados los campos legacy `Conductor.tracto_patente` /
    `modelo_tracto` (texto libre, usados por el formulario de "Nuevo
    Servicio" en `operaciones`) a partir de la FK real `Tracto.conductor`.

    Así el mantenedor de Tractos queda con una relación de verdad (un
    <select> a Conductor, no dos campos de texto para escribir a mano) y el
    flujo viejo que todavía lee el texto sigue funcionando sin tocarlo.
    """
    # Libera al conductor anterior si este tracto cambió de dueño.
    Conductor.objects.filter(tracto_patente=instance.patente).exclude(pk=instance.conductor_id).update(
        tracto_patente=None, modelo_tracto=None
    )
    if instance.conductor_id:
        Conductor.objects.filter(pk=instance.conductor_id).update(
            tracto_patente=instance.patente, modelo_tracto=instance.modelo
        )


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
