from datetime import timedelta

from django.utils import timezone

from .models import SesionSemanal


def iniciar_programa(perfil, ahora=None):
    """Las semanas se anclan al primer mensaje y no cambian por inactividad."""
    ahora = ahora or timezone.now()
    if perfil.inicio_programa is None:
        perfil.inicio_programa = ahora
        perfil.save(update_fields=['inicio_programa'])
        SesionSemanal.objects.bulk_create([
            SesionSemanal(usuario=perfil.usuario, numero=numero, inicio=ahora + timedelta(days=7 * (numero - 1)), fin=ahora + timedelta(days=7 * numero), estado='activa' if numero == 1 else 'pendiente')
            for numero in range(1, 5)
        ])


def actualizar_semanas(usuario=None, ahora=None):
    ahora = ahora or timezone.now()
    semanas = SesionSemanal.objects.all()
    if usuario is not None:
        semanas = semanas.filter(usuario=usuario)
    semanas.filter(inicio__lte=ahora, fin__gt=ahora).exclude(estado='activa').update(estado='activa')
    semanas.filter(fin__lte=ahora).exclude(estado='cerrada').update(estado='cerrada')


def sesion_json(sesion, ahora=None):
    ahora = ahora or timezone.now()
    # La representación puede consultarse sin modificar fechas ni estado en DB.
    estado = 'cerrada' if ahora >= sesion.fin else 'activa' if ahora >= sesion.inicio else 'pendiente'
    try:
        reporte_id = sesion.reporte.pk
    except SesionSemanal.reporte.RelatedObjectDoesNotExist:
        reporte_id = None
    return {'id': sesion.pk, 'numero': sesion.numero, 'inicio': sesion.inicio.isoformat(), 'fin': sesion.fin.isoformat(), 'estado': estado, 'reporte_id': reporte_id}
