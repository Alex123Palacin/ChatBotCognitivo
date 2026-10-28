from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('sesiones', '0001_initial')]
    operations = [migrations.AlterField(
        model_name='sesionsemanal', name='fin',
        field=models.DateTimeField(blank=True, null=True),
    )]
