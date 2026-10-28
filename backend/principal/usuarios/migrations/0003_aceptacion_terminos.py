from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0002_origen_datos')]

    operations = [
        migrations.AddField(
            model_name='perfil', name='terminos_version',
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name='perfil', name='terminos_aceptados_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
