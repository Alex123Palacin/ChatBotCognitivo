from datetime import timedelta
from contextlib import closing
import uuid

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ml.conversacion import responder_conversacion, responder_conversacion_stream
from ml.ollama import ErrorModelo
from sesiones.models import SesionSemanal
from sesiones.services import actualizar_semanas, iniciar_programa, sesion_json
from usuarios.models import Perfil
from .models import Mensaje


class ErrorChat(Exception):
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado


def historial_modelo(usuario, hasta=None, limite=24):
    mensajes = Mensaje.objects.filter(usuario=usuario)
    if hasta:
        mensajes = mensajes.filter(fecha__lte=hasta.fecha).exclude(pk=hasta.pk)
    ultimos = list(mensajes.order_by('-fecha', '-id')[:limite])
    ultimos.reverse()
    return [{'role': 'user' if m.remitente == 'usuario' else 'assistant', 'content': m.contenido} for m in ultimos]


def contexto_modelo(usuario, sesion):
    from ml.analisis import INDICADORES
    from reportes.models import Evidencia

    evidencias = Evidencia.objects.filter(mensaje__usuario=usuario).select_related('mensaje__sesion').order_by('-mensaje__fecha')
    presentes = set(evidencias.filter(mensaje__sesion=sesion).values_list('indicador', flat=True))
    primeros = Mensaje.objects.filter(usuario=usuario, remitente='usuario').order_by('fecha')[:2]
    citas = [f'Primeras palabras del estudiante: {m.contenido[:180]}' for m in primeros]
    citas += [f'Semana {e.mensaje.sesion.numero}: {INDICADORES[e.indicador]["nombre"]}; cita del estudiante: {e.cita[:180]}' for e in evidencias[:4] if e.indicador in INDICADORES]
    for numero in range(1, sesion.numero):
        previo = Mensaje.objects.filter(usuario=usuario, remitente='usuario', sesion__numero=numero).order_by('-fecha').first()
        if previo:
            citas.append(f'Último relato de la semana {numero}: {previo.contenido[:120]}')
    return {'nombre': usuario.first_name, 'semana': sesion.numero, 'total_semanas': 4, 'indicadores_pendientes': [codigo for codigo in INDICADORES if codigo not in presentes], 'resumen': '\n'.join(citas)[:1600]}


def chat_json(usuario):
    ahora = timezone.now()
    actualizar_semanas(usuario, ahora)
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    perfil.ultima_actividad = ahora
    perfil.conectado = True
    perfil.save(update_fields=['ultima_actividad', 'conectado'])
    sesiones = list(SesionSemanal.objects.filter(usuario=usuario).select_related('reporte'))
    actual = next((s for s in sesiones if s.inicio <= ahora < s.fin), None)
    mensajes = list(Mensaje.objects.filter(usuario=usuario).select_related('respuesta', 'sesion').order_by('fecha', 'id'))
    activo = bool(perfil.respuesta_hasta and perfil.respuesta_hasta > ahora)
    ultimo_sin_respuesta = next((m for m in reversed(mensajes) if m.remitente == 'usuario' and not hasattr(m, 'respuesta')), None)
    pendiente = None
    if ultimo_sin_respuesta:
        pendiente = {'clave_envio': str(ultimo_sin_respuesta.clave_envio), 'mensaje': ultimo_sin_respuesta.contenido, 'estado': 'pendiente' if activo else 'error'}
    return {
        'mensajes': [{'id': str(m.pk), 'contenido': m.contenido, 'remitente': m.remitente, 'fecha': m.fecha.isoformat(), 'sesion_numero': m.sesion.numero, **({'clave_envio': str(m.clave_envio), 'respuesta_estado': 'respondido' if hasattr(m, 'respuesta') else ('pendiente' if activo else 'error')} if m.remitente == 'usuario' else {})} for m in mensajes],
        'sesiones': [sesion_json(s) for s in sesiones],
        'sesion_actual': sesion_json(actual) if actual else None,
        'programa_finalizado': bool(sesiones and ahora >= sesiones[-1].fin),
        'respuesta_pendiente': activo,
        'mensaje_pendiente': pendiente,
    }


def _procesar_mensaje(usuario, contenido, clave_envio, en_flujo=False):
    if not isinstance(contenido, str) or not contenido.strip() or len(contenido) > 2000:
        raise ErrorChat('Escribe un mensaje de entre 1 y 2000 caracteres.')
    contenido = contenido.strip()
    try:
        clave = uuid.UUID(str(clave_envio))
    except (ValueError, AttributeError, TypeError):
        raise ErrorChat('El identificador del envío no es válido.')
    ahora = timezone.now()
    token = str(uuid.uuid4())
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    existente = Mensaje.objects.filter(usuario=usuario, clave_envio=clave).select_related('respuesta').first()
    if existente and existente.contenido != contenido:
        raise ErrorChat('Ese envío ya pertenece a otro mensaje.', 409)
    if existente and hasattr(existente, 'respuesta'):
        return
    # Una reserva persistida protege tanto dos pestañas como dos procesos Django.
    # La transacción termina ANTES de esperar al modelo: SQLite no queda bloqueado.
    with transaction.atomic():
        # El primer acceso de la transacción es una escritura para evitar una
        # conversión de bloqueo de lectura a escritura bajo concurrencia SQLite.
        adquirido = Perfil.objects.filter(pk=perfil.pk).filter(Q(respuesta_hasta__isnull=True) | Q(respuesta_hasta__lte=ahora)).update(respuesta_hasta=ahora + timedelta(seconds=240), respuesta_token=token)
        if not adquirido:
            raise ErrorChat('Tu respuesta sigue en proceso. Espera unos momentos.', 409)
        existente = Mensaje.objects.filter(usuario=usuario, clave_envio=clave).select_related('respuesta').first()
        if existente and existente.contenido != contenido:
            raise ErrorChat('Ese envío ya pertenece a otro mensaje.', 409)
        if existente and hasattr(existente, 'respuesta'):
            Perfil.objects.filter(pk=perfil.pk, respuesta_token=token).update(respuesta_hasta=None, respuesta_token='')
            return
        perfil.refresh_from_db()
        if not existente:
            sin_respuesta = Mensaje.objects.filter(usuario=usuario, remitente='usuario', respuesta__isnull=True).exists()
            if sin_respuesta:
                raise ErrorChat('Reintenta el último mensaje antes de enviar otro.', 409)
            iniciar_programa(perfil, ahora)
            sesion = SesionSemanal.objects.filter(usuario=usuario, inicio__lte=ahora, fin__gt=ahora).first()
            if not sesion:
                raise ErrorChat('Terminaste las cuatro semanas. Puedes consultar tu conversación.', 409)
            existente = Mensaje.objects.create(usuario=usuario, sesion=sesion, contenido=contenido, remitente='usuario', fecha=ahora, clave_envio=clave)
        else:
            existente.respuesta_error = ''
            existente.save(update_fields=['respuesta_error'])
    try:
        historial = historial_modelo(usuario, hasta=existente)
        historial.append({'role': 'user', 'content': existente.contenido})
        contexto = contexto_modelo(usuario, existente.sesion)
        if en_flujo:
            partes = []
            # Cerrar el navegador también cierra la conexión al modelo. No se
            # guarda una respuesta parcial como si estuviera terminada.
            with closing(responder_conversacion_stream(historial, contexto)) as flujo:
                for fragmento in flujo:
                    if not isinstance(fragmento, str):
                        raise ErrorModelo('El modelo devolvió una respuesta no válida.')
                    if fragmento:
                        partes.append(fragmento)
                        yield fragmento
            respuesta = ''.join(partes)
        else:
            respuesta = responder_conversacion(historial, contexto)
        if not isinstance(respuesta, str) or not respuesta.strip():
            raise ErrorModelo('El modelo no devolvió una respuesta. Vuelve a intentar.')
        with transaction.atomic():
            propietario = Perfil.objects.filter(pk=perfil.pk, respuesta_token=token).update(respuesta_hasta=timezone.now() + timedelta(seconds=5))
            if not propietario:
                raise ErrorChat('La espera venció. Reintenta tu mensaje para recuperar la respuesta.', 503)
            Mensaje.objects.get_or_create(respuesta_a=existente, defaults={'usuario': usuario, 'sesion': existente.sesion, 'contenido': respuesta.strip(), 'remitente': 'asistente', 'fecha': timezone.now(), 'analisis_estado': 'listo'})
    except ErrorModelo as exc:
        Mensaje.objects.filter(pk=existente.pk, usuario__perfil__respuesta_token=token).update(respuesta_error=str(exc))
        raise ErrorChat(str(exc), 503) from exc
    except GeneratorExit:
        Mensaje.objects.filter(pk=existente.pk, usuario__perfil__respuesta_token=token).update(respuesta_error='La conexión se interrumpió. Puedes reintentar el mensaje.')
        raise
    finally:
        Perfil.objects.filter(pk=perfil.pk, respuesta_token=token).update(respuesta_hasta=None, respuesta_token='')


def enviar_mensaje(usuario, contenido, clave_envio):
    # Conserva la API JSON anterior y las mismas reglas de persistencia.
    for _ in _procesar_mensaje(usuario, contenido, clave_envio):
        pass


def enviar_mensaje_flujo(usuario, contenido, clave_envio):
    return _procesar_mensaje(usuario, contenido, clave_envio, en_flujo=True)
