from datetime import timedelta

from django.utils import timezone
from django.db.models import Max

from .models import SesionSemanal


def iniciar_programa(perfil, ahora=None):
    """Compatibilidad con periodos históricos; el chat usa iniciar_conversacion."""
    ahora = ahora or timezone.now()
    if perfil.inicio_programa is None:
        perfil.inicio_programa = ahora
        perfil.save(update_fields=['inicio_programa'])
        SesionSemanal.objects.bulk_create([
            SesionSemanal(usuario=perfil.usuario, numero=numero, inicio=ahora + timedelta(days=7 * (numero - 1)), fin=ahora + timedelta(days=7 * numero), estado='activa' if numero == 1 else 'pendiente')
            for numero in range(1, 5)
        ])


def iniciar_conversacion(perfil, ahora=None):
    """Un periodo abierto, sin alterar las fechas ni mensajes de los anteriores.

    El llamador reserva el Perfil en una transacción antes de crear el periodo.
    No se asigna aquí una fecha ficticia de intervención o de cierre.
    """
    ahora = ahora or timezone.now()
    if perfil.inicio_programa is None:
        perfil.inicio_programa = ahora
        perfil.save(update_fields=['inicio_programa'])
    abierta = SesionSemanal.objects.filter(usuario=perfil.usuario, fin__isnull=True).first()
    if abierta is not None:
        return abierta
    siguiente = (SesionSemanal.objects.filter(usuario=perfil.usuario).aggregate(maximo=Max('numero'))['maximo'] or 0) + 1
    return SesionSemanal.objects.create(
        usuario=perfil.usuario, numero=siguiente, inicio=ahora, fin=None, estado='activa',
    )


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
    estado = 'cerrada' if sesion.fin is not None and ahora >= sesion.fin else 'activa' if ahora >= sesion.inicio else 'pendiente'
    try:
        reporte_id = sesion.reporte.pk
    except SesionSemanal.reporte.RelatedObjectDoesNotExist:
        reporte_id = None
    return {'id': sesion.pk, 'numero': sesion.numero, 'inicio': sesion.inicio.isoformat(), 'fin': sesion.fin.isoformat() if sesion.fin else None, 'estado': estado, 'reporte_id': reporte_id}
