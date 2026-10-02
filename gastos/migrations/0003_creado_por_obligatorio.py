import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gastos", "0002_alter_categoriagasto_centro_costo_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="gastoruta", name="creado_por",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gastos_creados", to=settings.AUTH_USER_MODEL),
        ),
    ]
