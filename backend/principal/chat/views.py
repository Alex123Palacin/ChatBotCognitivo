import json
from contextlib import closing

from django.http import JsonResponse, StreamingHttpResponse

from principal.http import acceso, datos_json, error
from .services import ErrorChat, chat_json, enviar_mensaje, enviar_mensaje_flujo


@acceso(['GET', 'POST'], estudiante=True)
def chat(request):
    if request.method == 'POST':
        datos = datos_json(request)
        try:
            enviar_mensaje(request.user, datos.get('mensaje'), datos.get('clave_envio'))
        except ErrorChat as exc:
            return error(str(exc), exc.estado)
    return JsonResponse(chat_json(request.user))


@acceso(['POST'], estudiante=True)
def chat_flujo(request):
    datos = datos_json(request)
    # Resuelve la sesión antes de empezar el flujo; no transmite datos de otro chat.
    usuario = request.user

    def evento(tipo, **datos):
        return json.dumps({'tipo': tipo, **datos}, ensure_ascii=False) + '\n'

    def contenido():
        yield evento('inicio')
        try:
            with closing(enviar_mensaje_flujo(usuario, datos.get('mensaje'), datos.get('clave_envio'))) as flujo:
                for fragmento in flujo:
                    yield evento('fragmento', contenido=fragmento)
            yield evento('estado', chat=chat_json(usuario))
        except ErrorChat as exc:
            yield evento('error', error=str(exc))

    respuesta = StreamingHttpResponse(contenido(), content_type='application/x-ndjson; charset=utf-8')
    respuesta['X-Accel-Buffering'] = 'no'
    respuesta['Cache-Control'] = 'no-store'
    return respuesta
