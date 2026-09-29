"""Registro central de mantenedores genéricos.

Cada entrada describe una tabla maestra y cómo debe listarse/editarse.
Agregar una tabla maestra nueva a la app solo requiere agregar una
entrada aquí: las vistas y templates de maestros/views.py son genéricas
y funcionan para cualquier modelo registrado.
"""

from collections import OrderedDict

from django.db.models import Q

from catalogos.models import Conductor, Tracto

from .models import (
    CentroCosto,
    Cliente,
    Comuna,
    FormaDePago,
    HorarioRecepcion,
    Local,
    Prioridad,
    Proveedor,
    Rampla,
    Region,
    Ruta,
    Tarifa,
    TipoRampla,
    TipoServicio,
)

# Metadatos visuales de cada grupo (orden en que aparecen en /maestros/).
GRUPOS = OrderedDict(
    [
        ("Comercial", {"icono": "💼", "descripcion": "Clientes, sus direcciones y las tarifas acordadas."}),
        ("Flota", {"icono": "🚛", "descripcion": "Equipos disponibles para operar los servicios."}),
        ("Ubicación", {"icono": "🗺️", "descripcion": "Geografía base para rutas y tarifas."}),
        ("Catálogos", {"icono": "🗂️", "descripcion": "Listas de referencia usadas en toda la operación."}),
    ]
)

MANTENEDORES = OrderedDict(
    [
        (
            "clientes",
            {
                "modelo": Cliente,
                "grupo": "Comercial",
                "icono": "🏢",
                "titulo": "Clientes",
                "titulo_singular": "Cliente",
                "nuevo_texto": "Nuevo cliente",
                "descripcion": "Razón social, RUT y contacto comercial.",
                "campos": [
                    "razon_social", "giro", "rut", "direccion",
                    "contacto_nombre", "contacto_telefono", "contacto_email",
                    "ejecutivo_comercial", "cupo",
                    "nombre_vendedor", "rut_vendedor", "correo_vendedor",
                    "condicion_pago", "es_directo", "activo",
                ],
                "columnas": ["razon_social", "rut", "contacto_nombre", "condicion_pago", "es_directo", "activo"],
                "busqueda": ["razon_social", "rut", "nombre_vendedor"],
            },
        ),
        (
            "locales",
            {
                "modelo": Local,
                "grupo": "Comercial",
                "icono": "📦",
                "titulo": "Locales",
                "titulo_singular": "Local",
                "nuevo_texto": "Nuevo local",
                "descripcion": "Direcciones de carga y descarga por cliente.",
                # "codigo" no va en campos: se autogenera solo al crear
                # (primera letra del cliente + correlativo), no se edita.
                "campos": [
                    "cliente", "nombre", "direccion", "comuna",
                    "horario_recepcion", "observacion", "activo",
                ],
                "columnas": ["nombre", "cliente", "codigo", "comuna", "horario_recepcion", "activo"],
                "busqueda": ["nombre", "codigo", "cliente__razon_social"],
            },
        ),
        (
            "tarifas",
            {
                "modelo": Tarifa,
                "grupo": "Comercial",
                "icono": "💲",
                "titulo": "Tarifas",
                "titulo_singular": "Tarifa",
                "nuevo_texto": "Nueva tarifa",
                "descripcion": "Valores acordados por cliente y ruta, por tipo de carga.",
                "campos": [
                    "cliente", "local", "ruta",
                    "seco", "frio", "congelado", "unica",
                    "vigente_desde", "vigente_hasta", "activa",
                ],
                "columnas": ["cliente", "local", "ruta", "seco", "frio", "congelado", "unica", "activa"],
                "busqueda": ["cliente__razon_social"],
                # El <select> de Local solo debe mostrar los locales del
                # cliente ya elegido (si no hay cliente todavía, vacío) —
                # se completa en vivo por htmx al cambiar el cliente, ver
                # _form_class en maestros/views.py.
                "querysets": {
                    # form.data trae el cliente recién elegido en el propio
                    # POST (aunque el resto del formulario no haya validado
                    # todavía); form.instance.cliente_id cubre el caso de
                    # edición, donde el formulario carga sin POST.
                    "local": lambda form: (
                        Local.objects.filter(
                            cliente_id=form.data.get("cliente") or form.instance.cliente_id
                        )
                        if (form.data.get("cliente") or form.instance.cliente_id)
                        else Local.objects.none()
                    ),
                },
            },
        ),
        (
            "formas-de-pago",
            {
                "modelo": FormaDePago,
                "grupo": "Comercial",
                "icono": "💳",
                "titulo": "Formas de pago",
                "titulo_singular": "Forma de pago",
                "nuevo_texto": "Nueva forma de pago",
                "descripcion": "Métodos de pago aceptados con clientes.",
                "campos": ["nombre", "observacion"],
                "columnas": ["nombre", "observacion"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "ramplas",
            {
                "modelo": Rampla,
                "grupo": "Flota",
                "icono": "🚛",
                "titulo": "Ramplas",
                "titulo_singular": "Rampla",
                "nuevo_texto": "Nueva rampla",
                "descripcion": "Equipos y su tipo de carrocería.",
                "campos": ["patente", "tipo_rampla", "es_externa", "proveedor", "activa", "observacion"],
                "columnas": ["patente", "tipo_rampla", "es_externa", "proveedor", "activa"],
                "busqueda": ["patente"],
            },
        ),
        (
            "tractos",
            {
                "modelo": Tracto,
                "grupo": "Flota",
                "icono": "🚚",
                "titulo": "Tractos",
                "titulo_singular": "Tracto",
                "nuevo_texto": "Nuevo tracto",
                "descripcion": "Camiones tracto: patente, marca, TAG y estado.",
                "campos": [
                    "patente", "marca", "modelo", "tipo_camion", "conductor",
                    "tag", "tarjeta_combustible", "proveedor_gps",
                    "estado", "observacion",
                ],
                "columnas": ["patente", "marca", "modelo", "conductor", "estado"],
                "busqueda": ["patente", "conductor__nombre"],
                # Un conductor no puede manejar dos tractos a la vez: el
                # <select> solo ofrece choferes sin tracto asignado, más el
                # que ya tiene asignado ESTE tracto (para no perderlo al
                # editar). Ver maestros/views.py::_form_class.
                "querysets": {
                    "conductor": lambda form: Conductor.objects.filter(
                        Q(tracto__isnull=True) | Q(pk=form.instance.conductor_id)
                    ).distinct(),
                },
            },
        ),
        (
            "conductores",
            {
                "modelo": Conductor,
                "grupo": "Flota",
                "icono": "🧑‍✈️",
                "titulo": "Conductores",
                "titulo_singular": "Conductor",
                "nuevo_texto": "Nuevo conductor",
                "descripcion": "Choferes de la flota y su tracto asignado.",
                "campos": [
                    "nombre", "rut", "telefono", "direccion",
                    "fecha_ingreso", "tipo_contrato", "estado", "observacion",
                ],
                # tracto_patente/modelo_tracto NO son editables acá a propósito:
                # se completan solos desde el mantenedor de Tractos (campo
                # `conductor`, ver catalogos/models.py _sincronizar_conductor_tracto).
                # Se muestran igual en la lista como referencia de solo lectura.
                "columnas": ["nombre", "rut", "telefono", "tracto_patente", "estado"],
                "busqueda": ["nombre", "rut"],
            },
        ),
        (
            "rutas",
            {
                "modelo": Ruta,
                "grupo": "Ubicación",
                "icono": "🧭",
                "titulo": "Rutas",
                "titulo_singular": "Ruta",
                "nuevo_texto": "Nueva ruta",
                "descripcion": "Combinaciones de comuna origen y destino.",
                "campos": ["comuna_origen", "comuna_destino", "kilometros", "activa"],
                "columnas": ["comuna_origen", "comuna_destino", "kilometros", "activa"],
                "busqueda": ["comuna_origen__nombre", "comuna_destino__nombre"],
            },
        ),
        (
            "comunas",
            {
                "modelo": Comuna,
                "grupo": "Ubicación",
                "icono": "📍",
                "titulo": "Comunas",
                "titulo_singular": "Comuna",
                "nuevo_texto": "Nueva comuna",
                "descripcion": "Comunas asociadas a cada región.",
                "campos": ["nombre", "region"],
                "columnas": ["nombre", "region"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "regiones",
            {
                "modelo": Region,
                "grupo": "Ubicación",
                "icono": "🌎",
                "titulo": "Regiones",
                "titulo_singular": "Región",
                "nuevo_texto": "Nueva región",
                "descripcion": "Regiones de Chile.",
                "campos": ["nombre"],
                "columnas": ["nombre"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "proveedores",
            {
                "modelo": Proveedor,
                "grupo": "Catálogos",
                "icono": "🤝",
                "titulo": "Proveedores",
                "titulo_singular": "Proveedor",
                "nuevo_texto": "Nuevo proveedor",
                "descripcion": "Terceros que prestan servicios a Transser.",
                "campos": ["nombre", "rut", "contacto_nombre", "contacto_telefono", "contacto_email", "activo"],
                "columnas": ["nombre", "rut", "contacto_nombre", "activo"],
                "busqueda": ["nombre", "rut"],
            },
        ),
        (
            "centros-costo",
            {
                "modelo": CentroCosto,
                "grupo": "Catálogos",
                "icono": "🏷️",
                "titulo": "Centros de costo",
                "titulo_singular": "Centro de costo",
                "nuevo_texto": "Nuevo centro de costo",
                "descripcion": "Centros de costo para gastos y facturación.",
                "campos": ["codigo", "nombre", "activo"],
                "columnas": ["codigo", "nombre", "activo"],
                "busqueda": ["codigo", "nombre"],
            },
        ),
        (
            "prioridades",
            {
                "modelo": Prioridad,
                "grupo": "Catálogos",
                "icono": "⭐",
                "titulo": "Prioridades",
                "titulo_singular": "Prioridad",
                "nuevo_texto": "Nueva prioridad",
                "descripcion": "Niveles de urgencia de un servicio.",
                "campos": ["nombre", "orden", "activo"],
                "columnas": ["nombre", "orden", "activo"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "tipos-servicio",
            {
                "modelo": TipoServicio,
                "grupo": "Catálogos",
                "icono": "🧩",
                "titulo": "Tipos de servicio",
                "titulo_singular": "Tipo de servicio",
                "nuevo_texto": "Nuevo tipo de servicio",
                "descripcion": "Categorías de servicio de transporte.",
                "campos": ["nombre", "descripcion", "activo"],
                "columnas": ["nombre", "activo"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "tipos-rampla",
            {
                "modelo": TipoRampla,
                "grupo": "Catálogos",
                "icono": "🔧",
                "titulo": "Tipos de rampla",
                "titulo_singular": "Tipo de rampla",
                "nuevo_texto": "Nuevo tipo de rampla",
                "descripcion": "Plana, furgón seco, furgón refrigerado, sider.",
                "campos": ["nombre", "activo"],
                "columnas": ["nombre", "activo"],
                "busqueda": ["nombre"],
            },
        ),
        (
            "horarios-recepcion",
            {
                "modelo": HorarioRecepcion,
                "grupo": "Catálogos",
                "icono": "🕒",
                "titulo": "Horarios de recepción",
                "titulo_singular": "Horario de recepción",
                "nuevo_texto": "Nuevo horario de recepción",
                "descripcion": "Ventanas horarias en que un local recibe carga.",
                "campos": ["nombre", "activo"],
                "columnas": ["nombre", "activo"],
                "busqueda": ["nombre"],
            },
        ),
    ]
)
