"""Registro conservador de frecuencias explícitas; no estima intensidad de estrés."""
import re
import unicodedata

FRECUENCIAS = {'nunca': 1, 'rara vez': 2, 'algunas veces': 3, 'casi siempre': 4, 'siempre': 5}
ETIQUETA = re.compile(r'\b(casi siempre|algunas veces|rara vez|nunca|siempre)\b')
SEMANA = re.compile(r'\b(?:esta semana|durante esta semana|en estos siete dias|en estos 7 dias)\b')
AMBIGUO = re.compile(r'\b(?:no siempre|no casi siempre|casi nunca|no se|no recuerdo|tal vez|quizas|creo que|antes|otra semana|semana pasada|el mes|cuando|si|podria|deberia|manana|ejemplo|inventado|mentira)\b')
RECURSOS = {'planificacion', 'automotivacion', 'busqueda_soporte'}
# La frecuencia debe modificar una acción propia del indicador en la misma cita.
ACCIONES = {
    'sobrecarga_academica': r'(?:tengo demasiad[ao]s? (?:tareas|trabajos|examenes)|me sobrepasan las tareas|se me acumulan las tareas|me siento sobrecargad[oa])',
    'presion_tiempo': r'(?:me falta tiempo|no me alcanza el tiempo|ando apurad[oa] con las tareas|voy apurad[oa] con las entregas)',
    'sintomas_fisicos': r'(?:me duele la cabeza|duermo mal|me siento cansad[oa]|me duele el estomago)',
    'sintomas_psicologicos': r'(?:me pongo nervios[oa]|me siento nervios[oa]|me preocupo|siento ansiedad|me cuesta concentrarme)',
    'planificacion': r'(?:hago (?:un |mi )?horario|organizo mis tareas|planifico mis tareas|anoto mis pendientes|ordeno mis tareas)',
    'automotivacion': r'(?:me animo|me motivo|me recuerdo mi meta|recuerdo mis avances|me propongo avanzar)',
    'busqueda_soporte': r'(?:pido ayuda|busco apoyo|consulto (?:a |al |con )|pregunto (?:a |al ))',
}
ESCUELA = re.compile(r'\b(?:colegio|clases|tareas|estudios|estudiar|examenes|examen|notas|matematica)\b')
PREGUNTAS = {
    'sobrecarga_academica': r'(?:tienes demasiadas tareas|te sientes sobrecargad[oa])',
    'presion_tiempo': r'(?:te falta tiempo|no te alcanza el tiempo)',
    'sintomas_fisicos': r'(?:te duele la cabeza|duermes mal|te sientes cansad[oa]|te duele el estomago)',
    'sintomas_psicologicos': r'(?:te pones nervios[oa]|te sientes nervios[oa]|te preocupas|sientes ansiedad|te cuesta concentrarte)',
    'planificacion': r'(?:haces (?:un |tu )?horario|organizas tus tareas|planificas tus tareas|anotas tus pendientes|ordenas tus tareas)',
    'automotivacion': r'(?:te animas|te motivas|te recuerdas tu meta|recuerdas tus avances|te propones avanzar)',
    'busqueda_soporte': r'(?:pides ayuda|buscas apoyo|consultas (?:a |al |con )|preguntas (?:a |al ))',
}


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.casefold()) if not unicodedata.combining(c))


def frecuencia_explicita(evidencia):
    """Solo acepta expresiones inequívocas respaldadas por la cita y su mensaje.

    No transforma cantidades de mensajes, intensidades, propuestas del asistente,
    ni frases ambiguas en una frecuencia. La extracción no llama a Ollama.
    """
    indicador, cita, mensaje = evidencia.indicador, evidencia.cita, evidencia.mensaje
    if indicador not in ACCIONES or mensaje.remitente != 'usuario' or mensaje.analisis_estado != 'listo' or not cita.strip() or cita not in mensaje.contenido:
        return None
    texto, contexto = normalizar(cita), normalizar(mensaje.contenido)
    if not SEMANA.search(contexto) or AMBIGUO.search(contexto):
        return None
    # Se rechazan citas que combinan más de una afirmación de frecuencia.
    etiquetas = list(ETIQUETA.finditer(texto))
    if len(etiquetas) != 1:
        return None
    etiqueta = etiquetas[0]
    accion = texto[etiqueta.end():].lstrip(' ,:')
    if not re.match(r'(?:yo )?' + ACCIONES[indicador] + r'\b', accion):
        return None
    valor = FRECUENCIAS[etiqueta.group()]
    # En afrontamiento se registra la frecuencia de USO, no de su dificultad.
    esperada = 'ausencia_explicita' if valor == 1 else ('recurso' if indicador in RECURSOS else 'dificultad')
    if evidencia.senal != esperada:
        return None
    if indicador in {'sintomas_fisicos', 'sintomas_psicologicos'} and not ESCUELA.search(texto):
        return None
    if indicador == 'sintomas_fisicos' and (not re.search(r'\bpor (?:los estudios|estudiar|las tareas|los examenes|el colegio)\b', texto) or re.search(r'\bno por\b', texto)):
        return None
    return valor


def frecuencia_respuesta(mensaje):
    """Admite «Casi siempre» solo tras una pregunta semanal inequívoca y cercana."""
    if mensaje.remitente != 'usuario' or mensaje.analisis_estado != 'listo':
        return {}
    texto = normalizar(mensaje.contenido).strip(' \t\n.!')
    if texto not in FRECUENCIAS:
        return {}
    pregunta = normalizar(getattr(mensaje, '_pregunta_frecuencia', ''))
    if pregunta.count('?') != 1 or not SEMANA.search(pregunta) or AMBIGUO.search(pregunta) or ETIQUETA.search(pregunta):
        return {}
    if not re.search(r'\b(?:con que frecuencia|que tan seguido|cada cuanto)\b', pregunta):
        return {}
    encontrados = [codigo for codigo, patron in PREGUNTAS.items() if re.search(patron, pregunta)]
    if len(encontrados) != 1 or not ESCUELA.search(pregunta):
        return {}
    codigo = encontrados[0]
    # No invierte preguntas negativas sobre el uso de un recurso.
    sin_presion_negativa = pregunta.replace('no te alcanza el tiempo', 'te falta tiempo')
    if re.search(r'\bno\b', sin_presion_negativa):
        return {}
    if codigo == 'sintomas_fisicos' and not re.search(r'\bpor (?:los estudios|estudiar|las tareas|los examenes|el colegio)\b', pregunta):
        return {}
    return {codigo: FRECUENCIAS[texto]}


def frecuencia_periodo(evidencias, indicador, mensajes=()):
    valores = {valor for e in evidencias if e.indicador == indicador and (valor := frecuencia_explicita(e)) is not None}
    valores.update(valor for mensaje in mensajes if (valor := frecuencia_respuesta(mensaje).get(indicador)) is not None)
    # No se promedian relatos contradictorios ni se elige el que parezca favorable.
    return valores.pop() if len(valores) == 1 else 'Sin información'
