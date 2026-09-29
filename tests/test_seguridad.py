import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from accounts.models import Usuario
from gastos.models import CategoriaGasto, GastoRuta
from operaciones.models import Servicio

PASSWORD = "Password123!"


@pytest.fixture
def usuarios(db):
    for rol in ("Administrador", "Operaciones", "Gerencia", "Consulta"):
        Group.objects.get_or_create(name=rol)

    creados = {}
    for nombre, email, rol in (
        ("Jorge Torres", "jorge@test.cl", "Administrador"),
        ("Alan Ponce", "alan@test.cl", "Operaciones"),
        ("Christian Carter", "christian@test.cl", "Gerencia"),
        ("Invitado", "invitado@test.cl", "Consulta"),
    ):
        usuario = Usuario.objects.create_user(email=email, nombre=nombre, password=PASSWORD)
        usuario.groups.add(Group.objects.get(name=rol))
        creados[email] = usuario
    return creados


@pytest.fixture
def tarifa(db):
    from maestros.models import Cliente, Comuna, Region, Ruta, Tarifa

    region = Region.objects.create(nombre="Región Metropolitana de Santiago")
    origen = Comuna.objects.create(nombre="Santiago", region=region)
    destino = Comuna.objects.create(nombre="Valparaíso", region=region)
    ruta = Ruta.objects.create(comuna_origen=origen, comuna_destino=destino)
    cliente = Cliente.objects.create(razon_social="Cliente Demo", rut="76.111.222-3")
    return Tarifa.objects.create(cliente=cliente, ruta=ruta, seco=100000, activa=True)


@pytest.fixture
def categoria(db):
    return CategoriaGasto.objects.create(codigo="PEAJE", grupo="Ruta", nombre="Peajes", activa=True)


def login(client, email, password=PASSWORD):
    return client.post(reverse("accounts:login"), {"email": email, "password": password})


def crear_servicio(client, tarifa):
    return client.post(reverse("operaciones:crear_servicio"), {
        "cliente": tarifa.cliente_id,
        "ruta": tarifa.ruta_id,
        "tipo_tarifa": "seco",
        "fecha_carga": "2026-08-05",
    })


# --- Login y rate limiting ---

def test_login_correcto(client, usuarios):
    respuesta = login(client, "jorge@test.cl")
    assert respuesta.status_code == 302


def test_login_password_incorrecta(client, usuarios):
    respuesta = login(client, "jorge@test.cl", password="mala-clave")
    assert respuesta.status_code == 200
    assert b"incorrectos" in respuesta.content


def test_login_bloquea_tras_intentos_fallidos(client, usuarios):
    for _ in range(5):
        login(client, "jorge@test.cl", password="mala-clave")
    # django-axes corta a nivel de middleware con 429, aunque la contraseña
    # del sexto intento ahora sea la correcta.
    respuesta = login(client, "jorge@test.cl")
    assert respuesta.status_code == 429


# --- Autenticación exigida ---

def test_centro_operaciones_requiere_login(client, usuarios):
    respuesta = client.get(reverse("operaciones:centro_operaciones"))
    assert respuesta.status_code == 302
    assert "/login/" in respuesta.url


def test_centro_operaciones_con_login_funciona(client, usuarios):
    login(client, "jorge@test.cl")
    respuesta = client.get(reverse("operaciones:centro_operaciones"))
    assert respuesta.status_code == 200


# --- RBAC: crear servicio (solo rol Operaciones) ---

def test_crear_servicio_con_rol_no_autorizado_da_403(client, usuarios, tarifa):
    for email in ("jorge@test.cl", "christian@test.cl", "invitado@test.cl"):
        login(client, email)
        respuesta = crear_servicio(client, tarifa)
        assert respuesta.status_code == 403, f"{email} no debería poder crear servicios"


def test_crear_servicio_con_rol_operaciones_funciona(client, usuarios, tarifa):
    login(client, "alan@test.cl")
    respuesta = crear_servicio(client, tarifa)
    assert respuesta.status_code == 302
    assert Servicio.objects.count() == 1


def test_crear_servicio_usa_identidad_real_no_falsificable(client, usuarios, tarifa):
    login(client, "alan@test.cl")
    client.post(reverse("operaciones:crear_servicio"), {
        "cliente": tarifa.cliente_id,
        "ruta": tarifa.ruta_id,
        "tipo_tarifa": "seco",
        "fecha_carga": "2026-08-05",
        "creado_por": "Un Impostor Cualquiera",
    })
    servicio = Servicio.objects.latest("id")
    assert servicio.creado_por == "Alan Ponce"
    assert servicio.eventos.first().actor == "Alan Ponce"


# --- RBAC: modificar tarifa (solo rol Administrador) ---

def test_modificar_tarifa_requiere_rol_administrador(client, usuarios, tarifa):
    login(client, "alan@test.cl")
    crear_servicio(client, tarifa)
    servicio = Servicio.objects.latest("id")

    login(client, "alan@test.cl")
    rechazado = client.post(reverse("operaciones:modificar_tarifa", args=[servicio.id]), {
        "tarifa_nueva": "150000", "motivo": "Ajuste de prueba",
    })
    assert rechazado.status_code == 403

    login(client, "jorge@test.cl")
    aceptado = client.post(reverse("operaciones:modificar_tarifa", args=[servicio.id]), {
        "tarifa_nueva": "150000", "motivo": "Ajuste de prueba",
    })
    assert aceptado.status_code == 302
    servicio.refresh_from_db()
    assert servicio.tarifa == 150000


# --- RBAC: aprobar gastos (solo Administrador o Gerencia) ---

def test_aprobar_gasto_con_rol_no_autorizado_da_403(client, usuarios, tarifa, categoria):
    login(client, "alan@test.cl")
    crear_servicio(client, tarifa)
    servicio = Servicio.objects.latest("id")

    client.post(reverse("gastos:crear_gasto", args=[servicio.id]), {
        "categoria_id": categoria.id, "fecha": "2026-08-05", "descripcion": "Peaje", "monto_neto": 5000,
    })
    gasto = GastoRuta.objects.latest("id")

    respuesta = client.post(reverse("gastos:cambiar_estado_gasto", args=[gasto.id]), {"estado": "Aprobado"})
    assert respuesta.status_code == 403


def test_aprobar_gasto_con_rol_gerencia_funciona_y_usa_identidad_real(client, usuarios, tarifa, categoria):
    login(client, "alan@test.cl")
    crear_servicio(client, tarifa)
    servicio = Servicio.objects.latest("id")

    client.post(reverse("gastos:crear_gasto", args=[servicio.id]), {
        "categoria_id": categoria.id, "fecha": "2026-08-05", "descripcion": "Peaje", "monto_neto": 5000,
    })
    gasto = GastoRuta.objects.latest("id")

    login(client, "christian@test.cl")
    respuesta = client.post(reverse("gastos:cambiar_estado_gasto", args=[gasto.id]), {"estado": "Aprobado"})
    assert respuesta.status_code == 302
    gasto.refresh_from_db()
    assert gasto.aprobado_por == "Christian Carter"
