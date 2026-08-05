from django.db import migrations

ROLES = ["Administrador", "Operaciones", "Gerencia", "Consulta"]


def crear_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for rol in ROLES:
        Group.objects.get_or_create(name=rol)


def eliminar_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [migrations.RunPython(crear_roles, eliminar_roles)]
