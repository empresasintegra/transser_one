from django import forms, template
from django.utils.html import format_html

register = template.Library()

# Campos que se muestran como "chip" monoespaciado (patentes, RUT, códigos).
_CAMPOS_MONO = {"patente", "rut", "codigo", "rut_vendedor"}

# Etiquetas (True, False) para campos booleanos cuyo nombre no es
# autoexplicativo con el genérico "Sí"/"No" — ej. es_directo.
_ETIQUETAS_BOOL = {
    "activo": ("Activo", "Inactivo"),
    "activa": ("Activa", "Inactiva"),
    "es_directo": ("Directo", "Indirecto"),
    "es_externa": ("Externa", "Propia"),
}


@register.filter
def get_attr(objeto, nombre_campo):
    """Devuelve el valor crudo de `objeto.nombre_campo` de forma dinámica."""
    valor = getattr(objeto, nombre_campo, "")
    if callable(valor):
        valor = valor()
    return valor


@register.filter
def verbose_name(nombre_campo, modelo):
    """Devuelve el verbose_name de un campo de un modelo, dado su nombre."""
    try:
        return modelo._meta.get_field(nombre_campo).verbose_name
    except Exception:
        # No es un campo de modelo (ej: una @property como "profit"): se
        # deriva un título legible a partir del nombre del atributo.
        return nombre_campo.replace("_", " ").capitalize()


@register.filter
def es_textarea(campo_formulario):
    """True si el widget del campo es un <textarea> — se usa para que ese
    campo ocupe todo el ancho del formulario en vez de una columna angosta."""
    return isinstance(campo_formulario.field.widget, forms.Textarea)


@register.filter
def toggle_orden(campo, orden_actual):
    """Valor que debería tener `?orden=` si el usuario hace click en la
    columna `campo`, dado el `?orden=` actual: asc -> desc -> asc..."""
    if orden_actual == campo:
        return f"-{campo}"
    return campo


@register.filter
def render_cell(objeto, nombre_campo):
    """Renderiza una celda de tabla según el tipo de dato del campo.

    Booleanos -> pill de estado. Patente/RUT/código -> chip monoespaciado.
    Vacío -> guion discreto. El resto, texto plano (auto-escapado por
    format_html).
    """
    valor = getattr(objeto, nombre_campo, None)
    if callable(valor):
        valor = valor()

    if isinstance(valor, bool):
        etiqueta_true, etiqueta_false = _ETIQUETAS_BOOL.get(nombre_campo, ("Sí", "No"))
        texto = etiqueta_true if valor else etiqueta_false
        clase = "pill-on" if valor else "pill-off"
        return format_html('<span class="status-pill {}">{}</span>', clase, texto)

    if valor is None or valor == "":
        return format_html('<span class="cell-empty">—</span>')

    if nombre_campo in _CAMPOS_MONO:
        return format_html('<span class="cell-mono">{}</span>', valor)

    return format_html("{}", valor)
