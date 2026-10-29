from datetime import datetime
from random import SystemRandom
from zoneinfo import ZoneInfo

from django.db import migrations


def seleccionar_si_procede(apps, schema_editor):
    """Solo inicializa la muestra autorizada de la población histórica exacta."""
    db = schema_editor.connection.alias
    Muestra = apps.get_model('reportes', 'MuestraEstudio')
    Mensaje = apps.get_model('chat', 'Mensaje')
    if Muestra.objects.using(db).filter(pk='estudio-20260911').exists():
        return
    lima = ZoneInfo('America/Lima')
    inicio = datetime(2026, 9, 11, 13, tzinfo=lima)
    fin = datetime(2026, 9, 11, 18, tzinfo=lima)
    ids = list(Mensaje.objects.using(db).filter(
        remitente='usuario', fecha__gte=inicio, fecha__lt=fin,
        usuario__is_staff=False, usuario__is_superuser=False,
    ).order_by('usuario_id').values_list('usuario_id', flat=True).distinct())
    # Una instalación vacía u otra población nunca se completa con cuentas ajenas.
    if len(ids) != 136:
        return
    muestra = Muestra.objects.using(db).create(
        clave='estudio-20260911', inicio=inicio, fin=fin,
        tamano=110, poblacion_ids=ids, metodo='aleatorio_simple_sin_reemplazo',
    )
    muestra.usuarios.set(SystemRandom().sample(ids, 110))


class Migration(migrations.Migration):
    dependencies = [('reportes', '0002_muestraestudio')]
    operations = [migrations.RunPython(seleccionar_si_procede, migrations.RunPython.noop)]
