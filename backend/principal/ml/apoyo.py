"""Recursos breves de autocuidado; no diagnostican ni puntúan indicadores.

Redacción propia basada en recursos públicos consultados el 31/10/2026:
OMS: https://www.who.int/thailand/activities/doing-what-matters-in-times-of-stress
NHS: https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/
NHS: https://www.nhs.uk/symptoms/chest-pain/
La selección por palabras es orientativa. El análisis de investigación sigue separado.
"""
import re
import unicodedata


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.casefold())
                   if not unicodedata.combining(c))


RECURSOS = {
    'anclaje': {
        'texto': 'Para volver al momento presente, nota tus pies apoyados en el suelo y nombra en silencio tres cosas que ves y un sonido que oyes, sin apurarte.',
        'marca': 'nota tus pies', 'ejercicio': True,
    },
    'pensamiento': {
        'texto': 'Puedes nombrarlo como «estoy teniendo el pensamiento de…» y completar la frase con lo que de verdad te preocupa. Notarlo así permite distinguir un pensamiento de un hecho, sin pelearte con lo que sientes.',
        'marca': 'estoy teniendo el pensamiento', 'ejercicio': True,
    },
    'respiracion': {
        'texto': 'Si te resulta cómodo, apoya los pies y deja entrar el aire suavemente por la nariz y salir por la boca a tu ritmo, sin forzarlo ni aguantarlo. Si te incomoda, para y vuelve a respirar normalmente.',
        'marca': 'sin forzarlo ni aguantarlo', 'ejercicio': True,
    },
    'apoyo': {
        'texto': 'No tienes que llevar esto sin compañía. Puedes contarle a un adulto de confianza o al orientador del colegio qué estás sintiendo y cómo te está afectando, para buscar apoyo juntos.',
        'marca': 'como te esta afectando', 'ejercicio': False,
    },
    'molestia': {
        'texto': 'Puedes hacer una pausa de lo que estás haciendo y buscar un lugar cómodo. Si la molestia sigue, se repite o te preocupa, cuéntaselo a un adulto de confianza para que te ayude a consultar a un profesional; no hay que dar por hecho que sea estrés.',
        'marca': 'no hay que dar por hecho que sea estres', 'ejercicio': False,
    },
}


def _mensaje_actual(historial):
    return next((m['content'] for m in reversed(historial)
                 if m.get('role') == 'user' and isinstance(m.get('content'), str)), '')


def _afirmaciones(texto):
    # Una negación de malestar no activa una intervención; 'no puedo dormir' sí.
    return [p for p in re.split(r'[,.!?;]|\bpero\b|\baunque\b|\by\b', normalizar(texto))
            if not re.search(r'\bno\s+(?:me\s+)?(?:tengo|siento|estoy|presento|duele)\b', p)]


def respuesta_prioritaria(historial):
    actual = normalizar(_mensaje_actual(historial))
    if re.search(r'\b(?:personaje|caso hipotetico|en un cuento|en el cuento|como ejemplo)\b', actual):
        return None
    texto = ' '.join(_afirmaciones(actual))
    if re.search(r'\b(?:me quiero matar|quiero matarme|quiero suicidarme|voy a suicidarme|me voy a hacer dano|no quiero seguir viviendo)\b', texto):
        return ('Lo que estás contando necesita apoyo ahora. Busca a un adulto de confianza, '
                'quédate acompañado y contacta con los servicios de emergencia locales si hay peligro inmediato. '
                '¿Estás a salvo en este momento?')
    pecho = re.search(r'\b(?:dolor|presion|aprieta|duele).{0,35}\bpecho\b', texto)
    if (re.search(r'\b(?:no puedo respirar|me cuesta respirar|me falta el aire|me desmaye)\b', texto)
            or (pecho and re.search(r'\b(?:fuerte|intenso|repentino|no se (?:va|quita)|sudor|mareo)\b', texto))):
        return ('Por lo que describes, no conviene asumir que sea estrés. Avisa ahora a un adulto cercano '
                'y busca atención médica urgente o los servicios de emergencia locales. '
                'No te quedes solo haciendo ejercicios para intentar que pase.')
    if pecho:
        return ('Una molestia en el pecho puede tener distintas causas y merece valoración médica. '
                'Avísale a un adulto de confianza para que te ayude a consultar; si es fuerte, repentina '
                'o aparece dificultad para respirar, busca atención urgente.')
    return None


def puede_preguntar(historial, preferencias):
    if preferencias.get('sin_preguntas'):
        return False
    if preferencias.get('preguntas_solicitadas'):
        return True
    asistentes = [m['content'] for m in historial if m.get('role') == 'assistant' and isinstance(m.get('content'), str)]
    # Deja al menos dos respuestas sin preguntas entre iniciativas del asistente.
    return not any(re.search(r'[?？﹖]', t) for t in asistentes[-2:])


def preparar_apoyo(historial, preferencias):
    """Un recurso por turno; escucha, cambios de tema y negaciones se respetan."""
    if preferencias.get('solo_escucha'):
        return None
    actual = normalizar(_mensaje_actual(historial))
    if re.search(r'\b(?:personaje|caso hipotetico|en un cuento|en el cuento|como ejemplo)\b', actual):
        return None
    asistentes = [normalizar(m['content']) for m in historial
                  if m.get('role') == 'assistant' and isinstance(m.get('content'), str)]
    if re.search(r'\b(?:ya estoy mejor|me siento mejor|me ayudo|me sirvio)\b', actual):
        return None
    texto = ' '.join(_afirmaciones(actual))
    seguimiento = bool(re.search(r'\b(?:no(?: me)? (?:funciono|sirvio|ayudo)|sigo igual|ya lo hice|lo intente)\b', actual)
                       or re.fullmatch(r'\s*(?:lo hice|si|dale|ok)[.! ]*', actual))
    if seguimiento:
        usuarios = [m['content'] for m in historial[:-1] if m.get('role') == 'user' and isinstance(m.get('content'), str)]
        temas = r'dolor|duele|molestia|tension|tembl|tiembl|nervios|preocup|ansied|miedo|angusti|estres|desbord|dormir|concentr|agotad|fatiga'
        if not re.search(temas, texto):
            texto = next((' '.join(_afirmaciones(t)) for t in reversed(usuarios)
                          if re.search(temas, ' '.join(_afirmaciones(t)))), '')
    if re.search(r'dolor|duele|molestia|cabeza|estomago|cuello|hombros|tension|tenso|tiembl|palpit|agotad|fatiga', texto):
        tema, opciones = 'malestar corporal relatado', ['anclaje', 'respiracion', 'molestia']
        if 'dolor' in texto or 'duele' in texto:
            opciones = ['molestia', 'anclaje', 'apoyo']
    elif re.search(r'nervios|preocup|ansied|miedo|angusti|estres|desbord|fracas|todo.*(?:mal|salir)', texto):
        tema, opciones = 'preocupación o nervios relatados', ['anclaje', 'pensamiento', 'apoyo']
        if re.search(r'pienso|imagino|fracasar|reir|equivoc|salir mal|saldra mal|temo que', texto):
            opciones = ['pensamiento', 'anclaje', 'apoyo']
    elif re.search(r'no puedo dormir|no logro dormir|insomnio|no puedo concentr|no logro concentr', texto):
        tema, opciones = 'descanso o concentración afectados', ['pensamiento', 'anclaje', 'apoyo']
    else:
        return None
    recientes = ' '.join(asistentes[-2:])
    for codigo in opciones:
        recurso = RECURSOS[codigo]
        if normalizar(recurso['marca']) in recientes:
            continue
        if preferencias.get('sin_ejercicios') and recurso['ejercicio']:
            continue
        if codigo == 'respiracion' and preferencias.get('sin_respiracion'):
            continue
        pregunta = ''
        if puede_preguntar(historial, preferencias) and not seguimiento:
            if tema == 'malestar corporal relatado' and not re.search(r'hoy|ayer|desde|hace|llevo|dias|semanas', actual):
                pregunta = '¿Esta molestia empezó hoy o lleva varios días?'
            elif tema == 'preocupación o nervios relatados' and not re.search(r'porque|por que|pienso|imagino|miedo de|temo que|reir|equivoc|examen|expon|exposicion|tarea|colegio', actual):
                pregunta = '¿Hay algo concreto que te esté preocupando ahora?'
        return {'tema': tema, 'codigo': codigo, 'texto': recurso['texto'], 'pregunta': pregunta}
    return None


def completar_apoyo(apoyo):
    return '\n\n' + apoyo['texto'] + ('\n\n' + apoyo['pregunta'] if apoyo['pregunta'] else '')
