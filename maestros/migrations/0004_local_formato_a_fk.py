"""Convierte Local.formato de texto libre a FK hacia FormatoLocal, sin
perder los datos que ya estaban cargados (ej. los 439 locales importados
del Excel de Walmart): primero renombra el campo de texto, agrega la FK
nueva, migra los datos de uno al otro, y recién ahí borra el texto viejo.
"""

from django.db import migrations, models
import django.db.models.deletion


def poblar_formato_fk(apps, schema_editor):
    Local = apps.get_model("maestros", "Local")
    FormatoLocal = apps.get_model("maestros", "FormatoLocal")
    cache = {}
    for local in Local.objects.exclude(formato_texto__isnull=True).exclude(formato_texto=""):
        texto = local.formato_texto.strip()
        if not texto:
            continue
        if texto not in cache:
            formato, _ = FormatoLocal.objects.get_or_create(nombre=texto)
            cache[texto] = formato
        local.formato = cache[texto]
        local.save(update_fields=["formato"])


def revertir_formato_fk(apps, schema_editor):
    Local = apps.get_model("maestros", "Local")
    for local in Local.objects.exclude(formato__isnull=True).select_related("formato"):
        local.formato_texto = local.formato.nombre
        local.save(update_fields=["formato_texto"])


class Migration(migrations.Migration):

    dependencies = [
        ("maestros", "0003_formatolocal"),
    ]

    operations = [
        migrations.RenameField(model_name="local", old_name="formato", new_name="formato_texto"),
        migrations.AddField(
            model_name="local",
            name="formato",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="locales", to="maestros.formatolocal",
            ),
        ),
        migrations.RunPython(poblar_formato_fk, revertir_formato_fk),
        migrations.RemoveField(model_name="local", name="formato_texto"),
    ]
