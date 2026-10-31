"""Lee la respuesta estructurada de conversación sin mostrar el JSON al alumno."""
import json
import re

from .ollama import ErrorModelo


def esquema_respuesta(permite_preguntas=False, max_caracteres=None):
    campo = {'type': 'string', 'minLength': 1}
    if not permite_preguntas:
        campo['pattern'] = (r'^[^¿?？﹖]{1,' + str(max_caracteres) + r'}$'
                            if max_caracteres else r'^[^¿?？﹖]+$')
    return {'type': 'object', 'properties': {'respuesta': campo},
            'required': ['respuesta'], 'additionalProperties': False}


def leer_respuesta(texto):
    try:
        datos = json.loads(texto)
    except (ValueError, TypeError) as exc:
        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.') from exc
    if not isinstance(datos, dict) or set(datos) != {'respuesta'}:
        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
    respuesta = datos['respuesta']
    if not isinstance(respuesta, str) or not respuesta.strip():
        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
    return respuesta


def _cadena_parcial(cadena):
    try:
        return json.JSONDecoder().raw_decode(cadena)
    except ValueError:
        # Retiene únicamente un escape o par UTF-16 incompleto al final.
        for recorte in range(min(13, len(cadena))):
            try:
                parcial = json.loads(cadena[:len(cadena)-recorte] + '"')
                parcial.encode('utf-8')
                return parcial, None
            except (ValueError, UnicodeError):
                pass
    return None, None


def texto_respuesta_flujo(fragmentos):
    """Decodifica el campo conforme llega, incluidos escapes JSON partidos."""
    acumulado, visible = '', ''
    for fragmento in fragmentos:
        acumulado += fragmento
        inicio = re.match(r'^\s*\{\s*"respuesta"\s*:\s*(")', acumulado)
        if inicio is None:
            continue
        cadena = acumulado[inicio.start(1):]
        parcial, _ = _cadena_parcial(cadena)
        if parcial is None:
            continue
        if not isinstance(parcial, str) or not parcial.startswith(visible):
            raise ErrorModelo('El modelo interrumpió su respuesta. Vuelve a intentarlo.')
        nuevo = parcial[len(visible):]
        visible = parcial
        if nuevo:
            yield nuevo
    completo = leer_respuesta(acumulado)
    if not completo.startswith(visible):
        raise ErrorModelo('El modelo interrumpió su respuesta. Vuelve a intentarlo.')
    if completo[len(visible):]:
        yield completo[len(visible):]


def sin_ofertas_repetidas(fragmentos):
    """Al pedir solo escucha, retira ofertas no solicitadas sin otra llamada al modelo."""
    pendiente, entregado = '', False
    def oferta(frase):
        return re.match(r'\s*(?:si\s+quieres\b|[¿？]?\s*te\s+gustar[ií]a\b)', frase, re.I)
    for fragmento in fragmentos:
        pendiente += fragmento
        while (corte := re.search(r'[.!?](?:\s+|$)', pendiente)) is not None:
            frase, pendiente = pendiente[:corte.end()], pendiente[corte.end():]
            if not oferta(frase):
                entregado = entregado or bool(frase.strip())
                yield frase
    if pendiente and not oferta(pendiente):
        entregado = True
        yield pendiente
    if not entregado:
        yield 'Podemos seguir conversando a tu ritmo.'


def limitar_preguntas(fragmentos, maximo=1):
    """Conserva el flujo inicial y retira preguntas adicionales, incluso sin ¿."""
    traduccion = str.maketrans({'؟':'?', '？':'?', '﹖':'?', '⸮':'?', '⁇':'?'})
    preguntas, pendiente, entregado = 0, '', False
    for fragmento in fragmentos:
        salida = []
        for letra in fragmento.translate(traduccion):
            if maximo is None or preguntas < maximo:
                salida.append(letra)
                if letra == '?':
                    preguntas += 1
            else:
                # Solo se retiene lo posterior a la última pregunta permitida.
                pendiente += letra
                if letra in '.!?\n':
                    if '?' not in pendiente and '¿' not in pendiente:
                        salida.append(pendiente)
                    pendiente = ''
        texto = ''.join(salida)
        if texto:
            entregado = entregado or bool(texto.strip())
            yield texto
    if pendiente and '?' not in pendiente and '¿' not in pendiente:
        entregado = entregado or bool(pendiente.strip())
        yield pendiente
    if not entregado:
        yield 'Podemos seguir a tu ritmo.'
