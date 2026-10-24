import hashlib
from django.db import migrations, models

# Huellas de las veinte identidades ficticias del lote colegio-20261023-20.
# No se usan IDs: no se marca ninguna cuenta ajena por coincidencia de número.
HUELLAS = {'2df27b7c2fb200df6211784820bc9f68aeec89852d1decf7ed0835edbf55d123', '7ad8ca04714af91071c4602e72905b9effa75356b78eb0b166ac35cd2b0711f9', '7bf56cfd5301ca417b4216132a7bf616eab482cd9ae66f3763be148f6b62851a', '07b948176a1a2260f92f910dc96866732c596aa8acb41f46b80851e5660d6180', '0dea637c2a2b23c18a9419840f827442d4f589bde5c50f659eca5e80c4a03be3', '2d51d50845b55fe0b2f520e7e1e988628ec8a9bd6eff201dbfe49a61c88311cb', '42777b00d410bf23b4a5a747ac59ec92fb795cc5509318ca6baf115493164b73', 'e26c80e7b27ef9e4e32bff4f30baffa9587016d122c953558fdf4a98673d5c3f', '25c297d7a9f708299e184e6f7623baac123b95333aebe93e6e61d0ddebe6a5c4', 'c55ae5d4907076881c011c20582eca949471bd4c9a39baf018eabb7baf1e8838', 'd138137d6b72140d70ae222b2845676ad91ae3d4b5596ea0c70b18cb670dd882', 'f8443c913813103d8487fd45ba883289c64d08db257c666584e69abaa5da7a20', '9e4eece10206bc3b0861de6bcfe1dea56d1c3feafacb24fa47874b7ee27dc686', 'c5c8996742cc74b02c40c24497a5bca59068bb5bf2b100f52aa64fe1a326559f', '0911d9f0f727a178e6f5d517e8c059cc7bd08678ef855e7b88d5178b0f6e24b6', 'e008ebf6dbf12a23b0ef2e69d4b93ea0f1b85dd896bd589e4cf04e5c9b1f8835', 'a22df7434b87a84291293bd476c553b7cfce283b8b54f6fa7b7ea7d92c955ce0', '053efc77f94b5a537c79323d792b04da09d7c1e9d89edd182b47f285e35b91e5', '0d54dae1ae2d34295a01488f5f03893b55e8ce2dcc89ba13b95a2547ac3633be', '0feebd212010f0ec7b9db66d9d96e8706f85baa9680efc3317a3d0969eb41323'}


def marcar_lote(apps, schema_editor):
    Perfil = apps.get_model('usuarios', 'Perfil')
    for perfil in Perfil.objects.using(schema_editor.connection.alias).select_related('usuario').filter(usuario__is_staff=False, usuario__is_superuser=False):
        if perfil.usuario.username == perfil.usuario.email and hashlib.sha256(perfil.usuario.username.encode()).hexdigest() in HUELLAS:
            perfil.origen_datos = 'demostracion'
            perfil.save(using=schema_editor.connection.alias, update_fields=['origen_datos'])


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0001_initial')]
    operations = [
        migrations.AddField(model_name='perfil', name='origen_datos', field=models.CharField(max_length=20, default='conversacion', choices=[('conversacion', 'Interacción registrada'), ('demostracion', 'Demostración')])),
        migrations.RunPython(marcar_lote, migrations.RunPython.noop),
    ]
