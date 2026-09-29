from collections import OrderedDict

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import ProtectedError, Q
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .mantenedores import GRUPOS, MANTENEDORES
from .models import Local

OPCIONES_POR_PAGINA = (10, 25, 50, 100)
POR_PAGINA_DEFAULT = 25


def _config(slug):
    try:
        return MANTENEDORES[slug]
    except KeyError:
        raise Http404(f"El mantenedor '{slug}' no existe.")


def _es_campo_ordenable(modelo, campo):
    """Solo se puede ordenar por columnas de modelo reales (no por
    @property calculadas como `Tarifa.profit`, que no existen en la BD)."""
    try:
        modelo._meta.get_field(campo)
        return True
    except Exception:
        return False


def _form_class(cfg):
    """Genera el ModelForm de un mantenedor.

    Dos comportamientos genéricos, disponibles para cualquier mantenedor
    por convención (sin tocar este archivo de nuevo):

    - Si la config trae `querysets` (dict campo -> callable(form) ->
      queryset), se recorta el `<select>` de ese campo a las opciones
      válidas — ej. en Tractos, que el conductor no muestre choferes ya
      asignados a otro tracto. El callable recibe el FORM completo (no
      solo `form.instance`) a propósito: en un POST fallido (ej. el
      usuario dejó otro campo obligatorio vacío), `form.instance` todavía
      no tiene el valor recién elegido en otro <select> del mismo POST
      — pero `form.data` sí, así que el resolver puede mirar cualquiera
      de los dos según haga falta (ver el de "local" en Tarifas, que
      depende del "cliente" elegido en el mismo formulario).
    - Si el formulario tiene a la vez un campo "cliente" y un campo
      "local", el <select> de cliente queda enganchado por htmx para que,
      al cambiarlo, se refresquen las opciones de "local" con solo las de
      ese cliente (ver `locales_de_cliente` y `maestros/urls.py`).
    """
    Form = modelform_factory(cfg["modelo"], fields=cfg["campos"])
    querysets = cfg.get("querysets") or {}
    cascada_cliente_local = "cliente" in cfg["campos"] and "local" in cfg["campos"]

    # Siempre se define la subclase (aunque no haya querysets ni cascada)
    # para poder parchar los widgets de fecha sobre la clase FINAL: Django
    # reconstruye `base_fields` desde cero para cada subclase de ModelForm
    # (ModelFormMetaclass), así que tocar `Form.base_fields` y subclasear
    # después descarta ese cambio — hay que hacerlo al revés.
    class FormPersonalizado(Form):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for campo, resolver in querysets.items():
                if campo in self.fields:
                    self.fields[campo].queryset = resolver(self)
            if cascada_cliente_local and "cliente" in self.fields:
                self.fields["cliente"].widget.attrs.update(
                    {
                        "hx-get": reverse("maestros:locales_de_cliente"),
                        "hx-trigger": "change",
                        "hx-target": "#id_local",
                        "hx-swap": "innerHTML",
                        "hx-include": "this",
                    }
                )

    # Cualquier campo de fecha (DateField, ej. Tarifa.vigente_desde,
    # Conductor.fecha_ingreso) usa el selector de calendario nativo del
    # navegador en vez de un <input type="text">. Se hace acá, una sola
    # vez por formulario generado, para que aplique a todos los
    # mantenedores sin tener que repetirlo en cada uno.
    for campo_formulario in FormPersonalizado.base_fields.values():
        if isinstance(campo_formulario, forms.DateField):
            campo_formulario.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            campo_formulario.input_formats = ["%Y-%m-%d"]

    return FormPersonalizado


@login_required
def locales_de_cliente(request):
    """Fragmento htmx: <option>s de Local filtradas por cliente.

    Usado para la cascada Cliente -> Local del formulario de Tarifas (ver
    form.html): al cambiar el <select> de cliente, se pide este fragmento
    y se reemplazan las opciones del <select> de local, para no mostrar
    locales de otro cliente.
    """
    cliente_id = request.GET.get("cliente")
    locales = Local.objects.filter(cliente_id=cliente_id).order_by("nombre") if cliente_id else Local.objects.none()
    return render(request, "maestros/_opciones_local.html", {"locales": locales})


@login_required
def index(request):
    grupos = OrderedDict()
    total_registros = 0
    for slug, cfg in MANTENEDORES.items():
        cantidad = cfg["modelo"].objects.count()
        total_registros += cantidad
        meta = GRUPOS.get(cfg["grupo"], {"icono": "🗂️", "descripcion": ""})
        grupo = grupos.setdefault(
            cfg["grupo"], {"icono": meta["icono"], "descripcion": meta["descripcion"], "items": []}
        )
        grupo["items"].append(
            {
                "slug": slug,
                "titulo": cfg["titulo"],
                "icono": cfg["icono"],
                "descripcion": cfg["descripcion"],
                "cantidad": cantidad,
            }
        )

    # Respeta el orden declarado en GRUPOS, no el orden de aparición.
    grupos_ordenados = OrderedDict((g, grupos[g]) for g in GRUPOS if g in grupos)

    contexto = {
        "grupos": grupos_ordenados,
        "total_registros": total_registros,
        "total_tablas": len(MANTENEDORES),
    }
    return render(request, "maestros/index.html", contexto)


@login_required
def lista(request, slug):
    cfg = _config(slug)
    objetos = cfg["modelo"].objects.all()

    busqueda = request.GET.get("q", "").strip()
    if busqueda and cfg.get("busqueda"):
        condiciones = Q()
        for campo in cfg["busqueda"]:
            condiciones |= Q(**{f"{campo}__icontains": busqueda})
        objetos = objetos.filter(condiciones)

    # Orden: ?orden=campo (ascendente) o ?orden=-campo (descendente). Solo
    # se acepta una columna que además esté declarada en cfg["columnas"] y
    # sea un campo real del modelo (evita ordenar por una @property o por
    # un campo que ni siquiera se muestra en la tabla).
    orden_param = request.GET.get("orden", "").strip()
    orden_campo = orden_param[1:] if orden_param.startswith("-") else orden_param
    orden_desc = orden_param.startswith("-")
    if orden_campo and orden_campo in cfg["columnas"] and _es_campo_ordenable(cfg["modelo"], orden_campo):
        objetos = objetos.order_by(orden_param)
    else:
        orden_param, orden_campo, orden_desc = "", "", False

    try:
        por_pagina = int(request.GET.get("por_pagina", POR_PAGINA_DEFAULT))
    except (TypeError, ValueError):
        por_pagina = POR_PAGINA_DEFAULT
    if por_pagina not in OPCIONES_POR_PAGINA:
        por_pagina = POR_PAGINA_DEFAULT

    paginador = Paginator(objetos, por_pagina)
    try:
        pagina = paginador.page(request.GET.get("page", 1))
    except PageNotAnInteger:
        pagina = paginador.page(1)
    except EmptyPage:
        pagina = paginador.page(paginador.num_pages)

    contexto = {
        "cfg": cfg,
        "slug": slug,
        "pagina": pagina,
        "busqueda": busqueda,
        "orden_param": orden_param,
        "orden_campo": orden_campo,
        "orden_desc": orden_desc,
        "por_pagina": por_pagina,
        "opciones_por_pagina": OPCIONES_POR_PAGINA,
    }
    # Las búsquedas/orden/paginación llegan vía htmx (ver list.html): en ese
    # caso alcanza con re-renderizar el fragmento de la tabla, no la página
    # completa. `request.htmx` lo da django-htmx (ya instalado).
    template = "maestros/_tabla.html" if request.htmx else "maestros/list.html"
    return render(request, template, contexto)


@login_required
def crear(request, slug):
    cfg = _config(slug)
    Form = _form_class(cfg)
    if request.method == "POST":
        form = Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['titulo_singular']} creado correctamente.")
            return redirect("maestros:lista", slug=slug)
    else:
        form = Form()
    return render(request, "maestros/form.html", {"cfg": cfg, "slug": slug, "form": form, "modo": "crear"})


@login_required
def editar(request, slug, pk):
    cfg = _config(slug)
    objeto = get_object_or_404(cfg["modelo"], pk=pk)
    Form = _form_class(cfg)
    if request.method == "POST":
        form = Form(request.POST, instance=objeto)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['titulo_singular']} actualizado correctamente.")
            return redirect("maestros:lista", slug=slug)
    else:
        form = Form(instance=objeto)
    return render(
        request, "maestros/form.html",
        {"cfg": cfg, "slug": slug, "form": form, "modo": "editar", "objeto": objeto},
    )


@login_required
@require_POST
def eliminar(request, slug, pk):
    cfg = _config(slug)
    objeto = get_object_or_404(cfg["modelo"], pk=pk)
    try:
        objeto.delete()
        messages.success(request, f"{cfg['titulo_singular']} eliminado.")
    except ProtectedError:
        messages.error(
            request,
            f"No se puede eliminar: este registro está siendo usado por otras tablas.",
        )
    return redirect("maestros:lista", slug=slug)
