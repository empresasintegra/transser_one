from django.db import models

from maestros.models import Proveedor


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
    # Transportista dueño del conductor. null=True solo para no romper los
    # conductores ya cargados; blank=False obliga a elegirlo en cualquier
    # formulario (mantenedor y admin) al crear o editar.
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, null=True, related_name="conductores",
        help_text="Proveedor (transportista) al que pertenece este conductor.",
    )
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
    class Estado(models.TextChoices):
        DISPONIBLE = "Disponible", "Disponible"
        EN_SERVICIO = "En servicio", "En servicio"
        EN_MANTENCION = "En mantención", "En mantención"
        FUERA_DE_SERVICIO = "Fuera de servicio", "Fuera de servicio"

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
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.DISPONIBLE)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["patente"]

    def __str__(self):
        return self.patente
