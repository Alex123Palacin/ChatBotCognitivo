"""Una sola fuente de análisis cualitativo y evidencias para el perfil y el Excel."""
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone
from chat.models import Mensaje
from sesiones.models import SesionSemanal
from ml.analisis import INDICADORES, SENALES_INDICADOR
from .models import Evidencia
from .estudio import acotar_mensajes
from .frecuencias import frecuencia_periodo


def datos_indicadores(usuarios, ahora=None):
    ahora = ahora or timezone.now()
    ids = [u.pk for u in usuarios]
    sesiones = {s.pk: s for s in SesionSemanal.objects.filter(usuario_id__in=ids)}
    mensajes = list(acotar_mensajes(Mensaje.objects.filter(usuario_id__in=ids, sesion_id__in=sesiones, fecha__lte=ahora)).order_by('fecha', 'pk')[:20001])
    if len(mensajes) > 20000:
        raise ValueError('La selección supera 20 000 mensajes. Descarga un grupo más pequeño.')
    mensajes = [m for m in mensajes if sesiones[m.sesion_id].usuario_id == m.usuario_id
                and sesiones[m.sesion_id].inicio <= m.fecha
                and (sesiones[m.sesion_id].fin is None or m.fecha < sesiones[m.sesion_id].fin)]
    anteriores = {}
    relatos = {m.pk: m for m in mensajes if m.remitente == 'usuario'}
    for mensaje in mensajes:
        previo = anteriores.get((mensaje.usuario_id, mensaje.sesion_id))
        padre = relatos.get(previo.respuesta_a_id) if previo else None
        if previo and padre and previo.remitente == 'asistente' and padre.usuario_id == mensaje.usuario_id and padre.sesion_id == mensaje.sesion_id and padre.fecha <= previo.fecha and timedelta(0) <= mensaje.fecha - previo.fecha <= timedelta(hours=2):
            mensaje._pregunta_frecuencia = previo.contenido
        anteriores[(mensaje.usuario_id, mensaje.sesion_id)] = mensaje
    mensajes = {m.pk: m for m in mensajes if m.remitente == 'usuario'}
    por_usuario, evidencias = defaultdict(list), defaultdict(list)
    for mensaje in mensajes.values():
        por_usuario[mensaje.usuario_id].append(mensaje)
    candidatas = list(Evidencia.objects.filter(mensaje_id__in=mensajes).order_by('mensaje__fecha', 'pk')[:60001])
    if len(candidatas) > 60000:
        raise ValueError('La selección tiene demasiadas evidencias. Descarga un grupo más pequeño.')
    for evidencia in candidatas:
        evidencia.mensaje = mensajes[evidencia.mensaje_id]
        # También las etiquetas y la síntesis requieren una cita literal analizada.
        if (evidencia.indicador not in INDICADORES
                or evidencia.senal not in SENALES_INDICADOR[evidencia.indicador]
                or evidencia.mensaje.analisis_estado != 'listo' or not evidencia.cita.strip()
                or evidencia.cita not in evidencia.mensaje.contenido):
            continue
        evidencias[evidencia.mensaje.usuario_id].append(evidencia)

    resultado = {}
    for usuario in usuarios:
        registros = por_usuario[usuario.pk]
        completo = bool(registros and all(m.analisis_estado == 'listo' for m in registros))
        resultado[usuario.pk] = {
            'mensajes': registros, 'evidencias': evidencias[usuario.pk], 'completo': completo,
            'frecuencias': {codigo: frecuencia_periodo(evidencias[usuario.pk], codigo, registros) if completo else 'Sin información' for codigo in INDICADORES},
        }
    return resultado


def evidencias_representativas(items, limite=3):
    """Conserva las distintas señales; la cantidad de citas no es gravedad."""
    elegidas, senales, citas = [], set(), set()
    for evidencia in reversed(items):
        if evidencia.senal not in senales:
            elegidas.append(evidencia)
            senales.add(evidencia.senal)
            citas.add(evidencia.cita)
    for evidencia in reversed(items):
        if len(elegidas) >= limite:
            break
        if evidencia.cita not in citas:
            elegidas.append(evidencia)
            citas.add(evidencia.cita)
    return sorted(elegidas[:limite], key=lambda e: (e.mensaje.fecha, e.pk))


def analisis_cualitativo(codigo, datos):
    meta = INDICADORES[codigo]
    items = [e for e in datos['evidencias'] if e.indicador == codigo]
    senales = {e.senal for e in items}
    pendientes = sum(m.analisis_estado != 'listo' for m in datos['mensajes'])
    representativas = evidencias_representativas(items)
    if len(senales) > 1:
        estado, etiqueta = 'relato_mixto', 'Relato mixto'
        analisis = ('El relato contiene distintas señales sobre este indicador. Se conservan las dificultades, '
                    'los recursos o las ausencias expresadas sin reducirlos a una única conclusión.')
    elif 'dificultad' in senales:
        estado, etiqueta = 'dificultad_reportada', 'Dificultad reportada'
        analisis = f'El estudiante relata dificultades relacionadas con {meta["nombre"].lower()}.'
    elif 'recurso' in senales:
        estado, etiqueta = 'recurso_reportado', 'Recurso utilizado'
        analisis = f'El estudiante describe el uso de {meta["nombre"].lower()} como recurso de afrontamiento.'
    elif 'ausencia_explicita' in senales:
        estado = 'ausencia_explicita'
        if meta['dimension'] == 'afrontamiento':
            etiqueta = 'Ausencia expresada del recurso'
            analisis = f'El estudiante expresa que no utiliza o no dispone del recurso de {meta["nombre"].lower()} en el contexto relatado.'
        else:
            etiqueta = 'Ausencia expresada'
            analisis = f'El estudiante niega expresamente dificultades relacionadas con {meta["nombre"].lower()} en el contexto relatado.'
    elif not datos['mensajes']:
        estado, etiqueta = 'sin_mensajes', 'Sin conversación registrada'
        analisis = 'No hay mensajes del estudiante dentro del periodo analizado. No se puede describir este indicador.'
    elif pendientes:
        estado, etiqueta = 'analisis_pendiente', 'Análisis pendiente'
        analisis = f'Este indicador todavía no tiene evidencia validada y quedan {pendientes} mensajes por analizar.'
    else:
        estado, etiqueta = 'no_mencionado', 'No mencionado en la conversación'
        analisis = 'El estudiante no menciona este tema en los mensajes analizados. No se puede confirmar su presencia ni su ausencia.'
    observaciones = list(dict.fromkeys(e.observacion.strip() for e in representativas if e.observacion.strip()))
    if observaciones:
        analisis += ' Observaciones registradas: ' + ' '.join(observaciones)
    if items and pendientes:
        analisis += f' La descripción es provisional: quedan {pendientes} mensajes por analizar.'
    return {
        'estado': estado, 'etiqueta': etiqueta, 'analisis': analisis,
        'evidencias': [{'cita': e.cita, 'observacion': e.observacion.strip() or 'Cita literal del estudiante.',
                        'fecha': e.mensaje.fecha.isoformat()} for e in representativas],
        'total_evidencias': len(items),
    }


def perfil_desde_datos(datos):
    """Construye el mismo resultado para la API y la descarga, sin nuevas inferencias."""
    indicadores, dificultades, recursos, sin_informacion = [], [], [], []
    for codigo, meta in INDICADORES.items():
        items = [e for e in datos['evidencias'] if e.indicador == codigo]
        senales = {e.senal for e in items}
        dificultad, recurso = 'dificultad' in senales, 'recurso' in senales
        if dificultad:
            dificultades.append(meta['nombre'])
        if recurso:
            recursos.append(meta['nombre'])
        if not items:
            sin_informacion.append(meta['nombre'])
        valor = datos['frecuencias'][codigo]
        indicadores.append({'id': codigo, 'nombre': meta['nombre'], 'dimension': meta['dimension'],
                            'frecuencia': valor if type(valor) is int else None,
                            'dificultad': dificultad, 'recurso': recurso,
                            'ausencia_explicita': 'ausencia_explicita' in senales, 'con_evidencia': bool(items),
                            **analisis_cualitativo(codigo, datos)})
    partes = []
    if dificultades:
        partes.append('En la conversación se expresan dificultades relacionadas con: ' + ', '.join(dificultades).lower() + '.')
    if recursos:
        partes.append('Se describen recursos de afrontamiento en: ' + ', '.join(recursos).lower() + '.')
    if sin_informacion:
        partes.append('No se mencionan en los mensajes analizados: ' + ', '.join(sin_informacion).lower() + '. Esto no confirma ausencia de dificultades.')
    if not dificultades and datos['evidencias']:
        partes.insert(0, 'Las citas disponibles no contienen dificultades expresadas; esto no permite afirmar ausencia de estrés.')
    pendientes = sum(m.analisis_estado != 'listo' for m in datos['mensajes'])
    if pendientes:
        partes.append(f'Quedan {pendientes} mensajes por analizar; la síntesis puede ampliarse.')
    if not datos['mensajes']:
        partes = ['No hay mensajes del estudiante dentro del periodo analizado.']
    return {'indicadores': indicadores, 'resumen': ' '.join(partes),
            'mensajes_analizados': len(datos['mensajes']) - pendientes, 'analisis_pendientes': pendientes}


def perfil_indicadores(usuario, ahora=None):
    return perfil_desde_datos(datos_indicadores([usuario], ahora)[usuario.pk])
