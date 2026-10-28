from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('chat', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='mensaje', name='eliminar_despues_de',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='mensaje', name='retencion_version',
            field=models.CharField(blank=True, max_length=60),
        ),
    ]
