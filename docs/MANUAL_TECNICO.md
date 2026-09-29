# Manual Técnico — Módulo `maestros`

Documentación para desarrolladores. Explica cómo está armado el código, por qué se tomaron ciertas decisiones, y cómo extenderlo.

---

## 1. Arquitectura del proyecto

Django 5.1, apps por dominio:

```
accounts/     Usuario custom (AUTH_USER_MODEL), login/logout, roles (grupos), decorador rol_requerido
catalogos/    Conductor, Tracto, TarifaMaestra (legacy — texto libre, en uso por operaciones)
maestros/     ← módulo nuevo de este trabajo: 14 modelos + sistema de mantenedores genérico
operaciones/  Servicio, EventoServicio, ComisionServicio (el core operativo, sigue en texto libre)
gastos/       CategoriaGasto, GastoRuta
```

`maestros` importa `catalogos.Conductor`/`catalogos.Tracto` para registrarlos en su sistema de mantenedores (ver §3), pero **no** modifica su relación con `operaciones.Servicio`.

---

## 2. Modelos (`maestros/models.py`)

14 modelos nuevos. Todos siguen la misma convención que ya usaba el resto del proyecto:

- `verbose_name`/`verbose_name_plural` explícitos en español (el auto-pluralizado de Django rompe con palabras como "región" → "regións").
- `Meta.ordering` definido siempre.
- `__str__` legible para que se vea bien en el admin y en los `<select>` de los formularios.
- Campos opcionales con `blank=True, null=True` juntos (no solo uno) — es la convención de Django para que tanto el formulario como la base de datos acepten vacío.

Relaciones a tener en cuenta:

- `Comuna.region`, `Local.comuna`, `Ruta.comuna_origen/destino` → `on_delete=PROTECT`: no se puede borrar una Región/Comuna si hay algo colgando de ella. Es intencional (ver §5.2, manejo de `ProtectedError`).
- `Local.cliente`, `Tarifa.cliente` → `on_delete=CASCADE`: si se borra un Cliente, sus Locales/Tarifas se van con él (a diferencia de la geografía, que es compartida entre clientes).
- `Rampla.proveedor`, `Tarifa.local` → `on_delete=SET_NULL` (con `null=True`): son relaciones opcionales, no tiene sentido bloquear el borrado del padre por esto.
- `Tarifa.profit` y `Tarifa.margen_pct` son **`@property`**, no columnas. Se calculan al vuelo desde `valor` y `costo` para que nunca queden desincronizadas — ver `maestros/models.py:261-271`.

```python
@property
def profit(self):
    if self.costo is None:
        return None
    return self.valor - self.costo
```

---

## 3. El sistema de mantenedores genérico

Esta es la pieza central del módulo. En vez de escribir una vista + template por cada una de las 16 tablas (list/create/update/delete × 16 = ~64 vistas casi idénticas), hay **un registro de configuración + 4 vistas genéricas + 3 templates genéricos** que sirven para cualquier modelo.

### 3.1 El registro (`maestros/mantenedores.py`)

Un diccionario ordenado (`MANTENEDORES`) donde cada entrada describe una tabla:

```python
MANTENEDORES = OrderedDict([
    ("clientes", {
        "modelo": Cliente,
        "grupo": "Comercial",
        "icono": "🏢",
        "titulo": "Clientes",
        "titulo_singular": "Cliente",
        "nuevo_texto": "Nuevo cliente",       # concordancia de género, ver §3.4
        "descripcion": "Razón social, RUT y contacto comercial.",
        "campos": [...],                       # qué campos van en el formulario (ModelForm)
        "columnas": [...],                      # qué columnas se muestran en la lista
        "busqueda": [...],                      # en qué campos busca el buscador (icontains, OR)
    }),
    ...
])
```

La clave del diccionario (`"clientes"`) es el **slug** que aparece en la URL: `/maestros/clientes/`.

`GRUPOS` (mismo archivo) define el orden y metadatos visuales de las 4 categorías que se ven en `/maestros/` (Comercial, Flota, Ubicación, Catálogos).

### 3.2 Las vistas (`maestros/views.py`)

Cuatro vistas, todas reciben el `slug` como parámetro y buscan la config en `MANTENEDORES`:

| Vista | URL | Qué hace |
|---|---|---|
| `index` | `/maestros/` | Agrupa todas las entradas de `MANTENEDORES` por grupo, cuenta registros de cada una |
| `lista` | `/maestros/<slug>/` | Lista + búsqueda (`Q()` OR sobre los campos de `busqueda`) |
| `crear` | `/maestros/<slug>/nuevo/` | `modelform_factory(modelo, fields=campos)` genera el `ModelForm` al vuelo |
| `editar` | `/maestros/<slug>/<pk>/editar/` | Igual que crear, pero con `instance=objeto` |
| `eliminar` | `/maestros/<slug>/<pk>/eliminar/` | `POST` con `try/except ProtectedError` |

La pieza clave es `django.forms.modelform_factory`: no hace falta declarar un `forms.ModelForm` por cada modelo — se construye dinámicamente a partir de la lista `campos` de la config.

```python
def _form_class(cfg):
    return modelform_factory(cfg["modelo"], fields=cfg["campos"])
```

`eliminar` captura `ProtectedError` (lanzado por Django cuando un FK con `on_delete=PROTECT` bloquea el borrado) y lo convierte en un mensaje de error legible en vez de un error 500.

### 3.3 Los templates (`maestros/templates/maestros/`)

Tres templates, reutilizados por las 16 tablas:

- `index.html`: la grilla de tarjetas agrupadas.
- `list.html`: tabla + buscador + botón nuevo. Itera `cfg.columnas` dinámicamente.
- `form.html`: itera `form` (el `ModelForm` generado) campo por campo. Detecta checkboxes (`field.field.widget.input_type == 'checkbox'`) para pintarlos como switch en vez de checkbox nativo.

Como el nombre del campo a mostrar es un **string dinámico** (viene de `cfg.columnas`), no se puede hacer `{{ objeto.campo }}` directo en el template (Django resuelve el nombre literal, no el valor de la variable). Por eso existen los template tags custom.

### 3.4 Template tags (`maestros/templatetags/maestros_extras.py`)

| Filtro | Uso | Qué hace |
|---|---|---|
| `get_attr` | `{{ objeto\|get_attr:campo }}` | `getattr(objeto, campo)` dinámico — soporta tanto campos de modelo como `@property` |
| `verbose_name` | `{{ campo\|verbose_name:cfg.modelo }}` | Encabezado de columna legible. Si `campo` no es un field real del modelo (ej. `profit`, que es una `@property`), cae al `except` y devuelve el nombre "humanizado" |
| `render_cell` | `{{ objeto\|render_cell:campo }}` | La celda completa ya renderizada (usa `format_html`, escapa el valor). Booleanos → pill de estado; `patente`/`rut`/`codigo` → chip monoespaciado; vacío → "—" |

`render_cell` tiene una regla de género hardcodeada a propósito, porque el español no es genérico:

```python
if nombre_campo == "activa":
    texto = "Activa" if valor else "Inactiva"
elif nombre_campo == "activo":
    texto = "Activo" if valor else "Inactivo"
```

Mismo motivo para `cfg["nuevo_texto"]` en el registro: en vez de derivar "Nuevo"/"Nueva" automáticamente (habría que mantener una lista de género por palabra), cada entrada de `MANTENEDORES` declara su propio texto completo ("Nueva tarifa", "Nuevo cliente"). Es más código pero cero ambigüedad.

### 3.5 Cómo agregar un mantenedor nuevo

Con este sistema, agregar una tabla maestra nueva **no requiere vistas ni templates nuevos**:

1. Definir el modelo en `maestros/models.py` (o el que corresponda).
2. `docker exec transser_django_web python manage.py makemigrations maestros && python manage.py migrate`.
3. Agregar una entrada a `MANTENEDORES` en `maestros/mantenedores.py` con `modelo`, `grupo`, `icono`, `titulo`, `titulo_singular`, `nuevo_texto`, `descripcion`, `campos`, `columnas`, `busqueda`.
4. (Opcional) Registrarlo también en `maestros/admin.py` si se quiere acceso desde `/admin/`.

Nada más. La URL, el listado, el buscador, el formulario y el borrado protegido funcionan solos.

---

## 4. Decisiones técnicas explicadas

### 4.1 Por qué no se tocó `operaciones.Servicio` todavía

`Servicio.cliente`, `conductor_principal`, `tracto`, `rampla` siguen siendo `CharField`. Convertirlos a FK habría exigido reescribir `crear_servicio`, `cambiar_rampla`, `modificar_tarifa` y sus templates (`operaciones/views.py`) **antes** de tener certeza sobre el modelo final — que solo se pudo validar después de revisar el Excel real de la empresa. Se prefirió construir el catálogo nuevo aparte (cero riesgo de romper lo que ya funcionaba) y dejar la conexión para una segunda etapa, ahora que el modelo ya está validado.

### 4.2 Por qué `Tracto`/`Conductor` sí se tocaron (pero solo se agregaron campos)

A diferencia de Cliente/Local/Tarifa (que no existían), `catalogos.Tracto` y `catalogos.Conductor` ya eran tablas reales con FK real (no texto libre). Agregarles campos nuevos (`marca`, `tag`, `tarjeta_combustible`, etc.) es una migración aditiva: ninguna vista ni template existente los lee ni los escribe, así que no hay forma de que rompan algo. Por eso se hizo directo, sin necesidad de aprobación adicional — es la misma categoría de cambio que agregar una columna nullable a cualquier tabla en producción.

### 4.3 Cache-busting del CSS

`templates/base.html` carga `{% static 'css/transser.css' %}?v=maestros1`. En `DEBUG=True` Django sirve estáticos directo desde disco sin hash de contenido, así que el navegador puede quedarse con una copia cacheada del CSS viejo entre ediciones. La query string `?v=...` fuerza al navegador a tratarlo como una URL distinta. **Hay que subir ese número manualmente** cada vez que se edite `transser.css` y se quiera forzar refresco en navegadores que ya visitaron el sitio (en producción, con `ManifestStaticFilesStorage`/Whitenoise, esto se resuelve solo vía hash de contenido).

### 4.4 Por qué los catálogos de tipo (`TipoTarifa`, `TipoRampla`, etc.) no son `TextChoices`

El resto del proyecto usa `models.TextChoices` para estados fijos (`Servicio.Estado`, `GastoRuta.Estado`). Se decidió **no** usar ese patrón para los tipos descubiertos en el Excel porque los valores reales son inconsistentes y van a seguir cambiando (aparecieron "Seco", "seco", "Multitemperatura", "Refrigerado", "Frío" como variantes sueltas). Un catálogo editable desde un mantenedor le permite al usuario de negocio estandarizar esos valores sin que un programador tenga que tocar código y desplegar.

---

## 5. Cómo correr el proyecto

```bash
docker compose up -d --build          # levanta django_db + django_web
docker exec transser_django_web python manage.py migrate
docker exec transser_django_web python manage.py seed_demo   # usuarios de prueba (ver manual de usuario)
```

La app queda en `http://localhost:8001` (puerto configurable en `.env` → `DJANGO_HOST_PORT`).

Para agregar migraciones tras editar modelos:

```bash
docker exec transser_django_web python manage.py makemigrations
docker exec transser_django_web python manage.py migrate
```

> El volumen de Postgres (`django_app_transser_django_postgres_data`) es local a este Docker Desktop. Si Docker se reinicia "en frío" (motor caído y reconstruido), el volumen puede aparecer vacío hasta que el motor termine de montar el disco — no asumas que los datos se perdieron solo porque `docker volume ls` sale vacío justo después de reiniciar Docker Desktop; espera a que el engine esté completamente arriba antes de concluir eso.

---

## 6. Deuda técnica conocida

- `Servicio`/`Conductor`/`Tracto`/`TarifaMaestra` (legacy) siguen sin conectar por FK a los catálogos nuevos.
- No existe todavía el dominio de Facturación/Cobranza (Factura, abonos, OC) que se ve en el Excel real.
- `Servicio` asume un solo destino por viaje; el Excel muestra viajes con hasta 8 paradas (`N° Locales`).
- No hay carga masiva (import) desde Excel/CSV hacia los mantenedores — la carga es manual, registro por registro, por ahora.
- `render_cell` tiene reglas de género (`activo`/`activa`) y de formato (`patente`/`rut`/`codigo`) hardcodeadas por nombre de campo. Si se agrega un mantenedor con un campo booleano de otro nombre, va a mostrar "Sí"/"No" genérico en vez de un texto más específico — no es un bug, es el fallback esperado.
