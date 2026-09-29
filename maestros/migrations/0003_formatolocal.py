from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("maestros", "0002_local_formato_tarifa_costo_alter_tarifa_valor"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormatoLocal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=60, unique=True)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "formato de local",
                "verbose_name_plural": "formatos de local",
                "ordering": ["nombre"],
            },
        ),
    ]
