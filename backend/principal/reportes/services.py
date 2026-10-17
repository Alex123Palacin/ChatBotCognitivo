from datetime import timedelta
import logging

from django.db import transaction
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from chat.models import Mensaje
from chat.services import historial_modelo
from ml.analisis import DIMENSIONES, INDICADORES, analizar_mensaje, sintetizar_indicador
from sesiones.models import SesionSemanal
from sesiones.services import actualizar_semanas
from usuarios.models import Perfil
from .models import Evidencia, ReporteSemanal

SENALES = {'dificultad', 'recurso', 'ausencia_explicita'}
logger = logging.getLogger(__name__)
NOTA_METODO = ('Análisis cualitativo orientativo de la conversación. Las citas pertenecen al estudiante y las observaciones son inferencias de IA. No es una puntuación SISCO ni un diagnóstico. La falta de evidencia no equivale a ausencia de estrés.')


def hay_respuesta_activa(ahora=None):
    """Todos los estudiantes comparten el mismo modelo local: el chat tiene prioridad."""
    return Perfil.objects.filter(respuesta_hasta__gt=ahora or timezone.now()).exists()


def analizar_pendiente(mensaje):
    ahora = timezone.now()
    if hay_respuesta_activa(ahora):
        return False
    duracion_reserva = max(1, settings.OLLAMA_ANALYSIS_TIMEOUT) + 60
    with transaction.atomic():
        adquirido = Mensaje.objects.filter(pk=mensaje.pk).exclude(analisis_estado='listo').filter(Q(analisis_hasta__isnull=True) | Q(analisis_hasta__lte=ahora)).update(analisis_estado='procesando', analisis_hasta=ahora + timedelta(seconds=duracion_reserva), analisis_intentos=F('analisis_intentos') + 1)
        if not adquirido:
            return False
        # Cada reserva tiene un número distinto. Se lee bajo el mismo bloqueo
        # que la asignación; la transacción termina antes de consultar Ollama.
        intento = Mensaje.objects.values_list('analisis_intentos', flat=True).get(pk=mensaje.pk)
    reserva = Mensaje.objects.filter(pk=mensaje.pk, analisis_intentos=intento, analisis_estado='procesando')
    try:
        resultados = analizar_mensaje(mensaje.contenido, historial_modelo(mensaje.usuario, hasta=mensaje, limite=10), cancelar=hay_respuesta_activa)
        if not isinstance(resultados, list):
            raise ValueError('El análisis no devolvió una lista de evidencias.')
        evidencias = []
        for item in resultados:
            if not isinstance(item, dict):
                continue
            indicador = item.get('indicador')
            cita = item.get('cita')
            observacion = item.get('observacion')
            senal = item.get('senal')
            if indicador not in INDICADORES or senal not in SENALES:
                continue
            if not isinstance(cita, str) or not cita.strip() or cita not in mensaje.contenido:
                continue
            if not isinstance(observacion, str) or not observacion.strip():
                continue
            evidencias.append(Evidencia(mensaje=mensaje, indicador=indicador, cita=cita[:2000], observacion=observacion[:1000], senal=senal))
        with transaction.atomic():
            # Esta escritura verifica la propiedad y obtiene el bloqueo antes
            # de insertar evidencias. Un worker vencido no altera la nueva reserva.
            if not reserva.update(analisis_estado='listo', analisis_hasta=None):
                return False
            Evidencia.objects.bulk_create(evidencias, ignore_conflicts=True)
        return True
    except Exception as exc:
        # El worker reintenta: jamás convierte un fallo del modelo en ausencia de evidencia.
        if hay_respuesta_activa():
            reserva.update(analisis_estado='pendiente', analisis_hasta=timezone.now() + timedelta(seconds=15))
            return False
        if reserva.update(analisis_estado='error', analisis_hasta=timezone.now() + timedelta(minutes=2)):
            logger.warning('Análisis pendiente del mensaje %s. Tipo de fallo: %s.', mensaje.pk, type(exc).__name__)
        return False


def actualizar_reporte(sesion):
    reporte, _ = ReporteSemanal.objects.get_or_create(sesion=sesion)
    mensajes = sesion.mensajes.filter(remitente='usuario')
    pendientes = mensajes.exclude(analisis_estado='listo').count()
    evidencias = Evidencia.objects.filter(mensaje__sesion=sesion)
    total = evidencias.count()
    cantidad = mensajes.count()
    indicadores = {e.indicador for e in evidencias}
    dias = len({timezone.localtime(fecha).date() for fecha in mensajes.values_list('fecha', flat=True)})
    if not cantidad:
        resumen = 'No hubo mensajes del estudiante durante esta semana. No existe información para describir los indicadores.'
    elif pendientes:
        resumen = f'Semana con {cantidad} mensajes del estudiante en {dias} días de conversación. El análisis sigue en preparación ({pendientes} mensajes pendientes).'
    elif not total:
        resumen = f'Se registraron {cantidad} mensajes en {dias} días de conversación. No se identificaron citas suficientes para describir los indicadores.'
    else:
        nombres = ', '.join(INDICADORES[codigo]['nombre'] for codigo in INDICADORES if codigo in indicadores)
        resumen = f'Se analizaron {cantidad} mensajes en {dias} días de conversación. Se encontraron {total} evidencias vinculadas con: {nombres}. Consulta las citas y observaciones por indicador.'
    nota = NOTA_METODO
    if cantidad < 3:
        nota += ' Información limitada por la cantidad de mensajes disponibles.'
    if pendientes:
        nota += ' Hay mensajes cuyo análisis está pendiente; las conclusiones todavía pueden ampliarse.'
    datos = {'estado': 'pendiente' if pendientes else 'listo', 'mensajes_estudiante': cantidad, 'total_evidencias': total, 'resumen': resumen, 'nota': nota}
    if any(getattr(reporte, clave) != valor for clave, valor in datos.items()):
        for clave, valor in datos.items():
            setattr(reporte, clave, valor)
        reporte.save()
    return reporte


def cerrar_y_actualizar_reportes(ahora=None):
    actualizar_semanas(ahora=ahora)
    for sesion in SesionSemanal.objects.filter(estado='cerrada').select_related('usuario'):
        actualizar_reporte(sesion)


def procesar_pendientes(limite=5, ahora=None):
    hora_inyectada = ahora
    ahora = ahora or timezone.now()
    cerrar_y_actualizar_reportes(ahora)
    if hay_respuesta_activa(ahora):
        return 0
    pendientes = Mensaje.objects.filter(remitente='usuario').exclude(analisis_estado='listo').filter(Q(analisis_hasta__isnull=True) | Q(analisis_hasta__lte=ahora)).filter(Q(usuario__perfil__respuesta_hasta__isnull=True) | Q(usuario__perfil__respuesta_hasta__lte=ahora)).select_related('usuario').order_by('fecha')[:limite]
    procesados = 0
    for mensaje in pendientes:
        procesados += analizar_pendiente(mensaje)
        # Un lote grande no retrasa el cierre hasta terminar todos los análisis.
        cerrar_y_actualizar_reportes(hora_inyectada)
    cerrar_y_actualizar_reportes(hora_inyectada)
    return procesados


def resumen_json(reporte):
    return {'id': reporte.pk, 'numero': reporte.sesion.numero, 'inicio': reporte.sesion.inicio.isoformat(), 'fin': reporte.sesion.fin.isoformat(), 'estado': reporte.estado, 'mensajes_estudiante': reporte.mensajes_estudiante, 'total_evidencias': reporte.total_evidencias, 'resumen': reporte.resumen}


def evidencias_sesion(sesion):
    candidatas = Evidencia.objects.filter(mensaje__sesion=sesion, mensaje__remitente='usuario', mensaje__analisis_estado='listo').select_related('mensaje').order_by('mensaje__fecha', 'pk')
    return [e for e in candidatas if e.indicador in INDICADORES and e.senal in SENALES and e.cita.strip() and e.cita in e.mensaje.contenido]


def dimensiones_sesion_json(sesion, evidencias=None):
    evidencias = evidencias if evidencias is not None else evidencias_sesion(sesion)
    dimensiones = []
    for codigo, nombre in DIMENSIONES.items():
        indicadores = []
        for indicador, metadata in INDICADORES.items():
            if metadata['dimension'] != codigo:
                continue
            items = [e for e in evidencias if e.indicador == indicador]
            conclusion = sintetizar_indicador([{'senal': e.senal, 'observacion': e.observacion} for e in items])
            indicadores.append({'id': indicador, 'nombre': metadata['nombre'], 'estado': 'con_evidencia' if items else 'sin_informacion', 'conclusion': conclusion, 'evidencias': [{'id': e.pk, 'mensaje_id': str(e.mensaje_id), 'cita': e.cita, 'observacion': e.observacion, 'senal': e.senal, 'fecha': e.mensaje.fecha.isoformat()} for e in items]})
        dimensiones.append({'id': codigo, 'nombre': nombre, 'indicadores': indicadores})
    return dimensiones


def dimensiones_json(reporte):
    return dimensiones_sesion_json(reporte.sesion)


def cobertura_conversacion(cantidad, analizados, evidencias):
    indicadores = {e.indicador for e in evidencias}
    dimensiones = {INDICADORES[codigo]['dimension'] for codigo in indicadores}
    pendientes = cantidad - analizados
    if not cantidad:
        estado = 'sin_mensajes'
        mensaje = 'El estudiante todavía no tiene mensajes en esta semana. No hay información para describir los indicadores.'
    elif pendientes:
        estado = 'analisis_pendiente'
        mensaje = f'Hay {pendientes} mensajes pendientes de analizar. Actualmente hay citas para {len(indicadores)} de 7 indicadores; la descripción puede ampliarse cuando termine el análisis.'
    elif not indicadores:
        estado = 'sin_evidencia'
        mensaje = 'Los mensajes disponibles se analizaron, pero no contienen citas suficientes para describir estos indicadores. El tiempo transcurrido no demuestra ausencia de estrés.'
    elif len(indicadores) < len(INDICADORES):
        estado = 'parcial'
        mensaje = f'Hay evidencia para describir {len(indicadores)} de 7 indicadores. Los demás siguen sin información suficiente; no se deduce que estén ausentes.'
    else:
        estado = 'completa'
        mensaje = 'Hay citas que respaldan los 7 indicadores y las 3 dimensiones. Esto describe la cobertura de la conversación; no es una puntuación SISCO ni un diagnóstico.'
    return {'estado': estado, 'indicadores_con_evidencia': len(indicadores), 'indicadores_totales': len(INDICADORES), 'dimensiones_con_evidencia': len(dimensiones), 'dimensiones_totales': len(DIMENSIONES), 'puede_describir_indicadores': bool(indicadores), 'mensaje': mensaje, 'indicadores_pendientes': [datos['nombre'] for codigo, datos in INDICADORES.items() if codigo not in indicadores], 'mensajes_analizados': analizados, 'analisis_pendientes': pendientes}


def reporte_actual_json(sesion, ahora=None):
    """Snapshot de lectura: no crea reportes ni solicita nuevas inferencias."""
    ahora = ahora or timezone.now()
    registros = list(sesion.mensajes.filter(remitente='usuario').values('fecha', 'analisis_estado'))
    cantidad = len(registros)
    analizados = sum(m['analisis_estado'] == 'listo' for m in registros)
    dias = len({timezone.localtime(m['fecha']).date() for m in registros})
    evidencias = evidencias_sesion(sesion)
    cobertura = cobertura_conversacion(cantidad, analizados, evidencias)
    resumen = f'Semana {sesion.numero}: {cantidad} mensajes del estudiante en {dias} días de conversación; {analizados} analizados y {cantidad - analizados} pendientes. Hay {len(evidencias)} citas para {cobertura["indicadores_con_evidencia"]} de 7 indicadores.'
    nota = NOTA_METODO + ' La cobertura indica qué temas tienen citas de respaldo, no la gravedad del estrés ni la validez de una medición. Los días y mensajes describen actividad, no minutos de conversación continua.'
    estado = 'finalizado' if ahora >= sesion.fin else 'en_curso'
    if estado == 'en_curso':
        nota += ' Vista de la semana en curso; el reporte semanal se generará al cierre.'
    return {'numero': sesion.numero, 'inicio': sesion.inicio.isoformat(), 'fin': sesion.fin.isoformat(), 'estado': estado, 'mensajes_estudiante': cantidad, 'total_evidencias': len(evidencias), 'resumen': resumen, 'nota': nota, 'dimensiones': dimensiones_sesion_json(sesion, evidencias), 'cobertura': cobertura}
