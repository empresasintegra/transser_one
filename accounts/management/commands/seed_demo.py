from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import Usuario

USUARIOS_DEMO = [
    ("Jorge Torres", "jorge@transser.cl", "Administrador"),
    ("Alan Ponce", "alan@transser.cl", "Operaciones"),
    ("Christian Carter", "christian@transser.cl", "Gerencia"),
]

PASSWORD_DEMO = "Transser2026!"

ROLES = ["Administrador", "Operaciones", "Gerencia", "Consulta"]


class Command(BaseCommand):
    help = "Crea los grupos de rol (si faltan) y los usuarios de demostración. Solo para desarrollo."

    def handle(self, *args, **options):
        for nombre_rol in ROLES:
            Group.objects.get_or_create(name=nombre_rol)

        for nombre, email, rol in USUARIOS_DEMO:
            usuario, creado = Usuario.objects.get_or_create(email=email, defaults={"nombre": nombre})
            if creado:
                usuario.set_password(PASSWORD_DEMO)
                usuario.save()
            usuario.groups.add(Group.objects.get(name=rol))
            estado = "creado" if creado else "ya existía"
            self.stdout.write(self.style.SUCCESS(f"Usuario {email} ({rol}) {estado}."))
