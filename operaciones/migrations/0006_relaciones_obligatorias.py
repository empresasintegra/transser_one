import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Hace obligatorias las relaciones de Servicio y tablas hijas.

    Se separó de la 0005 porque Django no puede agregar un FK NOT NULL sin
    default; las tablas estaban vacías al normalizar, así que el cambio a
    NOT NULL es seguro (si hubiera filas con NULL, esta migración falla
    en vez de dejar datos inconsistentes).
    """

    dependencies = [
        ("operaciones", "0005_remove_servicio_codigo_local_remove_servicio_destino_and_more"),
        ("maestros", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicio", name="cliente",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="servicios", to="maestros.cliente"),
        ),
        migrations.AlterField(
            model_name="servicio", name="ruta",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="servicios", to="maestros.ruta"),
        ),
        migrations.AlterField(
            model_name="servicio", name="creado_por",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="servicios_creados", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="eventoservicio", name="actor",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="eventos_realizados", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="comisionservicio", name="conductor",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="comisiones", to="catalogos.conductor"),
        ),
        migrations.AlterField(
            model_name="paradaservicio", name="creado_por",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="paradas_creadas", to=settings.AUTH_USER_MODEL),
        ),
    ]
