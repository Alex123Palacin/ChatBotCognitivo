"""Recalendario explícito del lote propio, preservando los turnos ya generados."""
import argparse
import copy
from datetime import datetime, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__:
    from .cargar import Carga, bloqueo, conectar, guardar
else:
    from cargar import Carga, bloqueo, conectar, guardar


def ajustar(carga, desde, hasta):
    from django.db import transaction
    from django.db.models import Max
    from django.utils import timezone
    from chat.models import Mensaje
    from reportes.services import actualizar_reporte
    from sesiones.models import SesionSemanal
    from usuarios.models import Perfil

    primero = datetime.combine(date.fromisoformat(desde), time(9), ZoneInfo('America/Lima'))
    fin = datetime.combine(date.fromisoformat(hasta), time(9), ZoneInfo('America/Lima'))
    dias = ((fin - timedelta(days=28)) - primero).days
    if dias < 0 or fin > timezone.now():
        raise ValueError('El rango debe permitir cuatro semanas de siete días, todas en el pasado.')
    if not (carga.carpeta / 'detener').exists():
        raise ValueError('Pausa el supervisor antes de ajustar las fechas.')
    personas = carga.personas
    usuarios = {p['clave']: carga.usuario(p['clave']) for p in personas}
    ids = [u.pk for u in usuarios.values()]
    if Perfil.objects.filter(usuario_id__in=ids, respuesta_hasta__gt=timezone.now()).exists():
        raise ValueError('Todavía hay una respuesta del lote activa. Espera a que termine.')
    anterior = copy.deepcopy(carga.manifiesto)
    nuevo = copy.deepcopy(anterior)
    nuevo['inicio'] = primero.isoformat()
    nuevo['calendario'] = {'desde': desde, 'hasta': hasta, 'visitas': 'inicio-fin', 'semanas_por_persona': 4, 'dias_por_semana': 7}
    for indice, p in enumerate(personas):
        inicio = primero + timedelta(days=dias * indice // max(1, len(personas) - 1))
        nuevo['cuentas'][p['clave']]['inicio'] = inicio.isoformat()
    respaldo = carga.carpeta / 'manifiesto-antes-del-calendario.json'
    if not respaldo.exists():
        guardar(respaldo, anterior)
    guardar(carga.carpeta / 'calendario-pendiente.json', {'desde': desde, 'hasta': hasta, 'fecha_operacion': timezone.now().isoformat()})
    carga.manifiesto = nuevo
    try:
        with transaction.atomic():
            # La escritura inicial serializa esta operación breve con el worker.
            Perfil.objects.filter(usuario_id__in=ids).update(conectado=False)
            for p in personas:
                u = carga.usuario(p['clave'])
                inicio = datetime.fromisoformat(nuevo['cuentas'][p['clave']]['inicio'])
                if u.semanas.count() != 4:
                    raise ValueError('Una cuenta no tiene exactamente cuatro sesiones.')
                conocidos = set()
                for numero, textos in enumerate(p['semanas'], 1):
                    sesion = SesionSemanal.objects.get(usuario=u, numero=numero)
                    sesion.inicio = inicio + timedelta(days=7 * (numero - 1))
                    sesion.fin = sesion.inicio + timedelta(days=7)
                    sesion.estado = 'cerrada'
                    sesion.save(update_fields=['inicio', 'fin', 'estado'])
                    for turno, contenido in enumerate(textos):
                        mid = carga.id_mensaje(p['clave'], numero, turno)
                        m = Mensaje.objects.filter(pk=mid).first()
                        if m is None:
                            continue
                        if m.usuario_id != u.pk or m.sesion_id != sesion.pk or m.remitente != 'usuario' or m.contenido != contenido:
                            raise ValueError('Un mensaje no coincide con el lote. No se cambiaron sus fechas.')
                        fecha = carga.fecha_visita(sesion, turno, len(textos))
                        Mensaje.objects.filter(pk=m.pk).update(fecha=fecha)
                        conocidos.add(m.pk)
                        for respuesta in Mensaje.objects.filter(respuesta_a=m):
                            if respuesta.usuario_id != u.pk or respuesta.sesion_id != sesion.pk or respuesta.remitente != 'asistente':
                                raise ValueError('Una respuesta no corresponde al estudiante esperado.')
                            Mensaje.objects.filter(pk=respuesta.pk).update(fecha=fecha + timedelta(seconds=20))
                            conocidos.add(respuesta.pk)
                if Mensaje.objects.filter(usuario=u).exclude(pk__in=conocidos).exists():
                    raise ValueError('Hay mensajes ajenos a las historias previstas. Se conservó el calendario anterior.')
                ultima = Mensaje.objects.filter(usuario=u).aggregate(fecha=Max('fecha'))['fecha']
                Perfil.objects.filter(usuario=u).update(inicio_programa=inicio, ultima_actividad=ultima, conectado=False)
                type(u).objects.filter(pk=u.pk).update(date_joined=inicio - timedelta(minutes=1))
                for sesion in u.semanas.all():
                    actualizar_reporte(sesion)
    except Exception:
        carga.manifiesto = anterior
        raise
    # Si se corta entre COMMIT y este archivo, repetir la misma operación es seguro.
    carga.inicio = primero
    carga.persistir()
    (carga.carpeta / 'calendario-pendiente.json').replace(carga.carpeta / 'calendario-aplicado.json')
    carga.exportar()
    carga.evento('calendario_ajustado', desde=desde, hasta=hasta, cuentas=len(ids), sesiones=len(ids) * 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--desde', required=True)
    parser.add_argument('--hasta', required=True)
    parser.add_argument('--lote', default='colegio-20261023-20')
    parser.add_argument('--backend', default='/app' if Path('/app/manage.py').exists() else str(Path(__file__).resolve().parents[2] / 'backend' / 'principal'))
    args = parser.parse_args()
    conectar(args.backend)
    carga = Carga(Path(__file__).with_name('historias.json'), args.carpeta, args.lote)
    with bloqueo(carga.carpeta):
        ajustar(carga, args.desde, args.hasta)


if __name__ == '__main__':
    main()
