"""Tablas maestras normalizadas de Transser One.

Estos modelos son NUEVOS y se agregan aparte de los que ya existen en
`catalogos` y `operaciones` (Conductor, Tracto, TarifaMaestra, Servicio),
que hoy guardan cliente/conductor/tracto/rampla como texto libre.

Por decisión explícita (ver conversación del 2026-08-10), estas tablas
todavía NO están conectadas por FK a Servicio/Conductor/Tracto: primero
se validan los campos reales contra los Excel que maneja hoy la empresa,
y luego se migra la relación. Mientras tanto quedan disponibles como
catálogos normalizados y con sus propios mantenedores.
"""

from django.db import models


class Region(models.Model):
    nombre = models.CharField("región", max_length=120, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "región"
        verbose_name_plural = "regiones"

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    nombre = models.CharField("comuna", max_length=120)
    region = models.ForeignKey(Region, related_name="comunas", on_delete=models.PROTECT, verbose_name="región")

    class Meta:
        ordering = ["region__nombre", "nombre"]
        verbose_name = "comuna"
        verbose_name_plural = "comunas"
        unique_together = [("nombre", "region")]

    def __str__(self):
        return f"{self.nombre} ({self.region.nombre})"


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=20, blank=True, null=True, unique=True)
    contacto_nombre = models.CharField(max_length=150, blank=True, null=True)
    contacto_telefono = models.CharField(max_length=30, blank=True, null=True)
    contacto_email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"

    def __str__(self):
        return self.nombre


class CentroCosto(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "centro de costo"
        verbose_name_plural = "centros de costo"

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Prioridad(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    orden = models.PositiveSmallIntegerField(default=0, help_text="Menor número = mayor prioridad.")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "prioridad"
        verbose_name_plural = "prioridades"

    def __str__(self):
        return self.nombre


class TipoServicio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"

    def __str__(self):
        return self.nombre


class TipoRampla(models.Model):
    """Ej: Plana, Furgón Seco, Furgón Refrigerado, Sider."""

    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de rampla"
        verbose_name_plural = "tipos de rampla"

    def __str__(self):
        return self.nombre


class HorarioRecepcion(models.Model):
    """Ventana horaria en la que un local recibe carga, ej: 08:00 - 12:00."""

    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "horario de recepción"
        verbose_name_plural = "horarios de recepción"

    def __str__(self):
        return self.nombre


class FormaDePago(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "forma de pago"
        verbose_name_plural = "formas de pago"

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    class CondicionPago(models.TextChoices):
        EFECTIVO = "Efectivo", "Efectivo"
        CHEQUE = "Cheque", "Cheque"

    razon_social = models.CharField("razón social", max_length=150)
    giro = models.CharField(max_length=150, blank=True, null=True)
    rut = models.CharField(max_length=20, unique=True)
    direccion = models.CharField("dirección", max_length=250, blank=True, null=True)
    contacto_nombre = models.CharField(max_length=150, blank=True, null=True)
    contacto_telefono = models.CharField(max_length=30, blank=True, null=True)
    contacto_email = models.EmailField(blank=True, null=True)
    ejecutivo_comercial = models.CharField(max_length=150, blank=True, null=True)
    cupo = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    # Pedido explícito del equipo comercial (no es lo mismo que el
    # ejecutivo_comercial de Transser): el vendedor es un dato del cliente.
    nombre_vendedor = models.CharField(max_length=150, blank=True, null=True)
    rut_vendedor = models.CharField(max_length=20, blank=True, null=True)
    correo_vendedor = models.EmailField(blank=True, null=True)
    condicion_pago = models.CharField(
        max_length=20, choices=CondicionPago.choices, blank=True, null=True,
    )
    es_directo = models.BooleanField(
        "cliente directo", default=True,
        help_text="Directo: compra directamente a Transser. Indirecto: a través de un intermediario.",
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["razon_social"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.razon_social


class Local(models.Model):
    """Dirección / sucursal de un cliente donde se carga o descarga."""

    cliente = models.ForeignKey(Cliente, related_name="locales", on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    # Autogenerado en save() (ver más abajo): primera letra del cliente +
    # correlativo, ej. "W0001". No es editable desde el formulario — los
    # códigos ya cargados del Excel (numéricos, reales de cada tienda) se
    # respetan tal cual, el autogenerado solo aplica a locales nuevos.
    codigo = models.CharField(max_length=30, blank=True, null=True, editable=False)
    direccion = models.CharField("dirección", max_length=250, blank=True, null=True)
    comuna = models.ForeignKey(Comuna, related_name="locales", on_delete=models.PROTECT, blank=True, null=True)
    horario_recepcion = models.ForeignKey(
        HorarioRecepcion, related_name="locales", on_delete=models.SET_NULL, blank=True, null=True,
    )
    observacion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["cliente__razon_social", "nombre"]
        verbose_name = "local"
        verbose_name_plural = "locales"

    def __str__(self):
        return f"{self.nombre} · {self.cliente.razon_social}"

    def save(self, *args, **kwargs):
        if not self.codigo and self.cliente_id:
            primera_letra = (self.cliente.razon_social or "?").strip()[:1].upper()
            correlativo = Local.objects.filter(cliente_id=self.cliente_id).count() + 1
            self.codigo = f"{primera_letra}{correlativo:04d}"
        super().save(*args, **kwargs)


class Rampla(models.Model):
    patente = models.CharField(max_length=20, unique=True)
    tipo_rampla = models.ForeignKey(TipoRampla, related_name="ramplas", on_delete=models.PROTECT, verbose_name="tipo de rampla")
    es_externa = models.BooleanField("es externa", default=False, help_text="Rampla de un proveedor externo, no propia de la flota.")
    proveedor = models.ForeignKey(
        Proveedor, related_name="ramplas", on_delete=models.SET_NULL, blank=True, null=True,
        help_text="Solo si la rampla es externa.",
    )
    activa = models.BooleanField(default=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["patente"]
        verbose_name = "rampla"
        verbose_name_plural = "ramplas"

    def __str__(self):
        return self.patente


class Ruta(models.Model):
    comuna_origen = models.ForeignKey(Comuna, related_name="rutas_origen", on_delete=models.PROTECT, verbose_name="comuna origen")
    comuna_destino = models.ForeignKey(Comuna, related_name="rutas_destino", on_delete=models.PROTECT, verbose_name="comuna destino")
    kilometros = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["comuna_origen__nombre", "comuna_destino__nombre"]
        verbose_name = "ruta"
        verbose_name_plural = "rutas"
        unique_together = [("comuna_origen", "comuna_destino")]

    def __str__(self):
        return f"{self.comuna_origen} → {self.comuna_destino}"


class Tarifa(models.Model):
    """Tarifa normalizada por cliente / local / ruta.

    Nota: esto es un catálogo NUEVO, independiente de `catalogos.TarifaMaestra`
    (que hoy usa el formulario de creación de servicios). Se conectará o
    reemplazará esa tabla una vez validados los campos con los Excel.

    Sin tipo de tarifa (se sacó): una misma Tarifa guarda hasta 4 valores
    simultáneos, uno por tipo de carga — igual que la hoja "Regiones" del
    Excel real, que trae Seco/Frío/Congelado en columnas separadas para el
    mismo destino en vez de una fila por tipo. `unica` es para rutas que no
    distinguen por temperatura (tarifa plana).
    """

    cliente = models.ForeignKey(Cliente, related_name="tarifas", on_delete=models.CASCADE)
    local = models.ForeignKey(Local, related_name="tarifas", on_delete=models.SET_NULL, blank=True, null=True)
    ruta = models.ForeignKey(Ruta, related_name="tarifas", on_delete=models.PROTECT)
    seco = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    frio = models.DecimalField("frío", max_digits=14, decimal_places=2, blank=True, null=True)
    congelado = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    unica = models.DecimalField(
        "única", max_digits=14, decimal_places=2, blank=True, null=True,
        help_text="Para rutas con tarifa plana, sin distinción por tipo de carga.",
    )
    vigente_desde = models.DateField(blank=True, null=True)
    vigente_hasta = models.DateField(blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["cliente__razon_social", "ruta"]
        verbose_name = "tarifa"
        verbose_name_plural = "tarifas"

    def __str__(self):
        return f"{self.cliente} · {self.ruta}"
