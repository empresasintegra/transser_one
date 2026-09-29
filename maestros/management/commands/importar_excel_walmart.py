"""Importa los catálogos maestros desde el Excel real de la empresa
("Walmart - transser actualizado.xlsx").

Uso:
    python manage.py importar_excel_walmart [--archivo RUTA] [--dry-run]

Por defecto lee `var/import/walmart_transser.xlsx` (relativo a BASE_DIR).

Qué importa, de qué hoja, y por qué:

- Hoja "Locales"  -> maestros.Cliente ("Walmart Chile") + maestros.Local
  (439 tiendas: nombre, código real de la tienda, dirección, comuna).
  La columna "Formato" de esa hoja ya no se importa (se sacó del modelo).
- Hoja "Regiones" -> maestros.Region, maestros.Comuna, maestros.Ruta,
  maestros.Tarifa (campos seco/frío/congelado/única por cliente y ruta).
  Esta hoja en realidad trae TRES tablas pegadas una debajo de otra con
  formatos distintos (ver comentarios en `_leer_regiones`): un tarifario
  nacional por región con 3 tipos de carga, y dos tarifarios más chicos
  (v/vi/vii región) con un solo valor — el segundo es una actualización
  parcial del primero, así que las tarifas que se repiten quedan la
  versión vieja con activa=False y la nueva con activa=True.
- Hoja "Transser" -> catalogos.Tracto y catalogos.Conductor (legacy,
  se les agregaron campos nuevos justamente para poder cargar esto).

La geografía (comuna -> región) no viene explícita para todas las filas
de "Locales" ni para el segundo/tercer bloque de "Regiones", así que se
resuelve con un mapa curado a mano (geografía real de Chile, no viene
del Excel). Cualquier comuna que no esté en ese mapa cae por defecto en
Región Metropolitana y queda listada al final del reporte para revisión
manual — Transser opera desde Santiago, así que es la región más
probable para lo no identificado, pero no es un hecho confirmado.

El comando es idempotente: se puede correr más de una vez sin duplicar
datos (usa get_or_create/update_or_create con una llave natural por
tabla).
"""

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.models import Conductor, Tracto
from maestros.models import Cliente, Comuna, Local, Region, Ruta, Tarifa

RUT_WALMART_PLACEHOLDER = "SIN-RUT-WALMART"  # Cliente.rut es max_length=20

RM = "Región Metropolitana de Santiago"


def normalizar(texto):
    """'Viña del Mar' / 'VIÑA DEL MAR' / 'Con-Con' -> 'VINA DEL MAR' / 'CON CON'."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[\s\-]+", " ", t).strip().upper()
    return t


# Mapa curado a mano: comuna/destino normalizado -> (nombre bonito, región bonita).
# Cubre las 53 filas del tarifario nacional (hoja Regiones, bloque 1), los
# ~55 destinos de los bloques 2/3 (V, VI y VII región) y las comunas propias
# de la hoja Locales que no aparecen en ningún tarifario. Todo lo que NO
# está acá cae por defecto en Región Metropolitana (ver `resolver_comuna`).
COMUNA_REGION = {}


def _reg(nombre_region, *comunas):
    for c in comunas:
        COMUNA_REGION[normalizar(c)] = (c, nombre_region)


_reg("Región de Tarapacá", "Alto Hospicio", "Iquique")
_reg("Región de Antofagasta", "Antofagasta", "Calama")
_reg("Región de Atacama", "Copiapó")
_reg("Región de Coquimbo", "Coquimbo", "Illapel", "La Serena", "Ovalle", "Salamanca", "Vicuña")
_reg(
    "Región de Valparaíso",
    "Algarrobo", "Cabildo", "Cartagena", "Casablanca", "Concón", "Curauma",
    "El Quisco", "La Calera", "La Ligua", "Limache", "Los Andes", "Maitencillo",
    "Puchuncaví", "Quillota", "Quilpué", "Quintero", "Reñaca", "San Antonio",
    "San Felipe", "Valparaíso", "Villa Alemana", "Viña del Mar",
)
_reg(
    "Región del Libertador General Bernardo O'Higgins",
    "Chimbarongo", "Graneros", "Las Cabras", "Machalí", "Pichilemu",
    "Rancagua", "Rengo", "Requínoa", "San Fernando", "San Francisco de Mostazal",
    "San Vicente de Tagua Tagua", "Santa Cruz",
)
_reg(
    "Región del Maule",
    "Cauquenes", "Constitución", "Curicó", "Linares", "Longaví", "Molina",
    "Parral", "San Clemente", "San Javier", "Talca", "Teno",
)
_reg(
    "Región del Biobío",
    "Arauco", "Cabrero", "Chiguayante", "Chillán", "Concepción", "Coronel",
    "Curanilahue", "Hualpén", "Hualqui", "Lebu", "Los Ángeles", "Lota",
    "Mulchén", "Nacimiento", "Penco", "San Carlos", "San Pedro de la Paz",
    "Talcahuano", "Tomé",
)
_reg(
    "Región de la Araucanía",
    "Angol", "Carahue", "Collipulli", "Lautaro", "Loncoche", "Nueva Imperial",
    "Padre Las Casas", "Pucón", "Temuco", "Traiguén", "Victoria", "Villarrica", "Vilcún",
)
_reg("Región de Los Lagos", "Alerce", "Castro", "Frutillar", "Osorno", "Puerto Montt", "Puerto Varas", "Purranque")
_reg("Región de Los Ríos", "La Unión", "Mariquina", "Río Bueno", "Valdivia")
_reg("Región de Arica y Parinacota", "Arica")
_reg("Región de Magallanes y de la Antártica Chilena", "Punta Arenas")
_reg("Región de Ñuble", "Quillón")
# Alias de escritura / typos vistos en el Excel que no matchean por acentos:
COMUNA_REGION[normalizar("Puert Montt")] = ("Puerto Montt", "Región de Los Lagos")
COMUNA_REGION[normalizar("Con-Con")] = ("Concón", "Región de Valparaíso")
COMUNA_REGION[normalizar("Mostazal")] = ("San Francisco de Mostazal", "Región del Libertador General Bernardo O'Higgins")
COMUNA_REGION[normalizar("San Vicente de Tagua Tagu")] = (
    "San Vicente de Tagua Tagua", "Región del Libertador General Bernardo O'Higgins",
)

# Comunas de la Región Metropolitana que sí aparecen explícitas en la hoja
# Locales (para que salgan con el nombre bien escrito en vez de "por defecto").
_reg(
    RM,
    "Buin", "Calera de Tango", "Cerrillos", "Cerro Navia", "Colina", "Conchalí",
    "Curacaví", "El Bosque", "El Monte", "Estación Central", "Huechuraba",
    "Independencia", "Isla de Maipo", "La Cisterna", "La Florida", "La Granja",
    "La Pintana", "La Reina", "Lampa", "Las Condes", "Lo Barnechea", "Lo Espejo",
    "Lo Prado", "Macul", "Maipú", "Melipilla", "Ñuñoa", "Padre Hurtado", "Paine",
    "Pedro Aguirre Cerda", "Peñaflor", "Peñalolén", "Providencia", "Pudahuel",
    "Puente Alto", "Quilicura", "Quinta Normal", "Recoleta", "Renca",
    "San Bernardo", "San Joaquín", "San Miguel", "San Ramón", "Santiago",
    "Talagante", "Vitacura",
)

COMUNAS_INVALIDAS = {normalizar("Nº 3200")}  # dato mal cargado en el Excel (número de local, no comuna)


def resolver_comuna(texto_crudo, no_identificadas):
    """Devuelve (nombre_bonito, region_bonita) o None si no se pudo resolver."""
    if not texto_crudo or not str(texto_crudo).strip():
        return None
    clave = normalizar(texto_crudo)
    if clave in COMUNAS_INVALIDAS:
        return None
    if clave in COMUNA_REGION:
        return COMUNA_REGION[clave]
    # No identificada: se asume Región Metropolitana (Transser opera desde
    # Santiago) pero se deja registrada para que el usuario la revise.
    no_identificadas.add(str(texto_crudo).strip())
    return (str(texto_crudo).strip(), RM)


def obtener_comuna(texto_crudo, no_identificadas, cache):
    resuelto = resolver_comuna(texto_crudo, no_identificadas)
    if resuelto is None:
        return None
    nombre, region_nombre = resuelto
    llave = (normalizar(nombre), normalizar(region_nombre))
    if llave in cache:
        return cache[llave]
    region, _ = Region.objects.get_or_create(nombre=region_nombre)
    comuna, _ = Comuna.objects.get_or_create(nombre=nombre, region=region)
    cache[llave] = comuna
    return comuna


def parsear_monto(valor):
    """'$251.708' / 251708.0 / None -> Decimal o None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor)).quantize(Decimal("1"))
    texto = re.sub(r"[^\d]", "", str(valor))
    if not texto:
        return None
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def parsear_fecha(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%d-%m-%y", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Importa Clientes, Locales, Regiones/Comunas, Rutas, Tarifas y Flota desde el Excel real de la empresa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            default=str(settings.BASE_DIR / "var" / "import" / "walmart_transser.xlsx"),
            help="Ruta al archivo .xlsx a importar.",
        )
        parser.add_argument("--dry-run", action="store_true", help="No guarda nada, solo simula y reporta.")

    def handle(self, *args, **options):
        ruta_archivo = options["archivo"]
        dry_run = options["dry_run"]
        self.stdout.write(f"Leyendo {ruta_archivo} ...")
        wb = openpyxl.load_workbook(ruta_archivo, data_only=True)

        self.no_identificadas = set()
        self.avisos = []
        self.comuna_cache = {}
        self.contadores = {}

        with transaction.atomic():
            self._importar_flota(wb["Transser"])
            self._importar_regiones(wb["Regiones"])
            self._importar_locales(wb["Locales"])
            if dry_run:
                self.stdout.write(self.style.WARNING("--dry-run: se revierte todo, no se guardó nada."))
                transaction.set_rollback(True)

        self._reporte()

    # ------------------------------------------------------------------
    def _contar(self, clave):
        self.contadores[clave] = self.contadores.get(clave, 0) + 1

    # ------------------------------------------------------------------
    def _importar_flota(self, ws):
        """Hoja 'Transser': un tracto + su conductor por fila."""
        for r in range(2, ws.max_row + 1):
            patente = ws.cell(row=r, column=4).value
            if not patente:
                continue
            marca = ws.cell(row=r, column=1).value
            modelo = (ws.cell(row=r, column=2).value or "").strip() or None
            tipo_camion = ws.cell(row=r, column=3).value
            nombre_conductor = ws.cell(row=r, column=5).value
            rut_conductor = ws.cell(row=r, column=6).value
            direccion = ws.cell(row=r, column=7).value
            ingreso = ws.cell(row=r, column=8).value
            contrato = ws.cell(row=r, column=9).value
            tag = ws.cell(row=r, column=10).value
            petroleo = ws.cell(row=r, column=11).value
            status = ws.cell(row=r, column=12).value
            gps = ws.cell(row=r, column=13).value

            patente = str(patente).strip().replace(" ", "").upper()
            nombre_conductor = (nombre_conductor or "").strip() or None
            rut_conductor = (rut_conductor or "").strip() or None

            # El Conductor se crea/actualiza primero para poder colgar la FK
            # real Tracto.conductor (en vez de duplicar nombre/rut como texto).
            conductor_obj = None
            if nombre_conductor:
                lookup = {"rut": rut_conductor} if rut_conductor else {"nombre": nombre_conductor}
                conductor_obj, _ = Conductor.objects.update_or_create(
                    **lookup,
                    defaults=dict(
                        nombre=nombre_conductor,
                        rut=rut_conductor,
                        direccion=direccion,
                        fecha_ingreso=parsear_fecha(ingreso),
                        tipo_contrato=contrato,
                    ),
                )
                self._contar("conductores")

            Tracto.objects.update_or_create(
                patente=patente,
                defaults=dict(
                    marca=marca,
                    modelo=modelo,
                    tipo_camion=tipo_camion,
                    conductor=conductor_obj,
                    tag=tag,
                    tarjeta_combustible=petroleo,
                    proveedor_gps=gps,
                    estado="Disponible" if status == "Entregado" else (status or "Disponible"),
                ),
            )
            self._contar("tractos")

    # ------------------------------------------------------------------
    def _importar_locales(self, ws):
        """Hoja 'Locales': Cliente Walmart + sus tiendas."""
        cliente, creado = Cliente.objects.get_or_create(
            rut=RUT_WALMART_PLACEHOLDER,
            defaults=dict(razon_social="Walmart Chile", giro="Retail / Supermercados"),
        )
        if creado:
            self.avisos.append(
                f"Cliente 'Walmart Chile' creado con RUT provisorio "
                f"'{RUT_WALMART_PLACEHOLDER}' — corregirlo con el RUT real en Maestros → Clientes."
            )
        self._contar("clientes")

        for r in range(2, ws.max_row + 1):
            nombre = ws.cell(row=r, column=2).value
            if not nombre:
                continue
            codigo = ws.cell(row=r, column=1).value
            # Columna 3 (Formato) ya no se importa: se sacó del modelo Local.
            direccion = ws.cell(row=r, column=4).value
            comuna_texto = ws.cell(row=r, column=5).value

            comuna = obtener_comuna(comuna_texto, self.no_identificadas, self.comuna_cache)

            Local.objects.update_or_create(
                cliente=cliente,
                codigo=str(codigo) if codigo is not None else None,
                nombre=str(nombre).strip(),
                defaults=dict(
                    direccion=direccion,
                    comuna=comuna,
                ),
            )
            self._contar("locales")

    # ------------------------------------------------------------------
    def _importar_regiones(self, ws):
        """Hoja 'Regiones': en realidad son 3 tablas apiladas, ver docstring del módulo."""
        cliente, _ = Cliente.objects.get_or_create(
            rut=RUT_WALMART_PLACEHOLDER,
            defaults=dict(razon_social="Walmart Chile", giro="Retail / Supermercados"),
        )
        origen = obtener_comuna("Santiago", self.no_identificadas, self.comuna_cache)

        # --- Bloque 1: filas 3-55, columnas A=Región B=Destino C-E=Tarifa(Seco/Frío/Congelado) F-H=Costo ---
        # Una Tarifa por (cliente, ruta), con los 3 valores en el mismo
        # registro (no una fila por tipo) — así queda igual que la hoja
        # real, que trae Seco/Frío/Congelado en columnas para un mismo
        # destino. El costo de esas columnas ya no se importa (se sacó
        # del modelo Tarifa).
        for r in range(3, 56):
            destino = ws.cell(row=r, column=2).value
            if not destino:
                continue
            comuna = obtener_comuna(destino, self.no_identificadas, self.comuna_cache)
            ruta = self._obtener_ruta(origen, comuna)
            if ruta is None:
                self.avisos.append(f"Fila {r} de 'Regiones' (bloque nacional) sin comuna válida: {destino!r} — se omitió.")
                continue
            seco = parsear_monto(ws.cell(row=r, column=3).value)
            frio = parsear_monto(ws.cell(row=r, column=4).value)
            congelado = parsear_monto(ws.cell(row=r, column=5).value)
            if seco is None and frio is None and congelado is None:
                continue
            Tarifa.objects.update_or_create(
                cliente=cliente, ruta=ruta,
                defaults=dict(seco=seco, frio=frio, congelado=congelado, activa=True),
            )
            self._contar("tarifas")

        # --- Bloques 2 y 3: [Destino, Costo Viaje, Valor Contrato] ---
        # Sin desglose por temperatura -> va a "unica". El costo tampoco se
        # importa acá (columna 2 del bloque, se descarta).
        bloque_2 = self._leer_bloque_simple(ws, 60, 101)
        bloque_3 = self._leer_bloque_simple(ws, 105, 125)
        destinos_actualizados = {normalizar(d) for d, _, _ in bloque_3}

        # `unica` se incluye en la llave de búsqueda (no solo en defaults) a
        # propósito: así la tarifa "vieja" (bloque 2) y la "actualizada"
        # (bloque 3) de un mismo destino quedan como DOS filas distintas en
        # vez de que la segunda pase por encima de la primera, y una
        # segunda corrida del importador no duplica ninguna de las dos.
        for destino, _costo, valor in bloque_2:
            comuna = obtener_comuna(destino, self.no_identificadas, self.comuna_cache)
            ruta = self._obtener_ruta(origen, comuna)
            if ruta is None:
                self.avisos.append(f"'Regiones' bloque 2, destino {destino!r} sin comuna válida — se omitió.")
                continue
            vigente = normalizar(destino) not in destinos_actualizados
            Tarifa.objects.update_or_create(
                cliente=cliente, ruta=ruta, unica=valor,
                defaults=dict(activa=vigente),
            )
            self._contar("tarifas")

        for destino, _costo, valor in bloque_3:
            comuna = obtener_comuna(destino, self.no_identificadas, self.comuna_cache)
            ruta = self._obtener_ruta(origen, comuna)
            if ruta is None:
                self.avisos.append(f"'Regiones' bloque 3, destino {destino!r} sin comuna válida — se omitió.")
                continue
            Tarifa.objects.update_or_create(
                cliente=cliente, ruta=ruta, unica=valor,
                defaults=dict(activa=True),
            )
            self._contar("tarifas")

    def _leer_bloque_simple(self, ws, fila_inicio, fila_fin):
        filas = []
        for r in range(fila_inicio, fila_fin + 1):
            destino = ws.cell(row=r, column=1).value
            if not destino or str(destino).strip().lower() in ("local",):
                continue
            costo = parsear_monto(ws.cell(row=r, column=2).value)
            valor = parsear_monto(ws.cell(row=r, column=3).value)
            if valor is None:
                continue
            filas.append((str(destino).strip(), costo, valor))
        return filas

    def _obtener_ruta(self, origen, destino):
        if origen is None or destino is None:
            return None
        ruta, _ = Ruta.objects.get_or_create(comuna_origen=origen, comuna_destino=destino)
        return ruta

    # ------------------------------------------------------------------
    def _reporte(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Importación terminada:"))
        for clave, cantidad in self.contadores.items():
            self.stdout.write(f"  {clave}: {cantidad}")
        self.stdout.write(f"  regiones en catálogo: {Region.objects.count()}")
        self.stdout.write(f"  comunas en catálogo: {Comuna.objects.count()}")
        self.stdout.write(f"  rutas en catálogo: {Ruta.objects.count()}")

        if self.avisos:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Avisos:"))
            for aviso in self.avisos:
                self.stdout.write(f"  - {aviso}")

        if self.no_identificadas:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"{len(self.no_identificadas)} comuna(s) no estaban en el mapa curado y se "
                    f"asignaron por defecto a '{RM}' — revisar que sea correcto:"
                )
            )
            for nombre in sorted(self.no_identificadas):
                self.stdout.write(f"  - {nombre}")
