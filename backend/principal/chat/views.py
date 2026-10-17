from django.http import JsonResponse

from principal.http import acceso, datos_json, error
from .services import ErrorChat, chat_json, enviar_mensaje


@acceso(['GET', 'POST'], estudiante=True)
def chat(request):
    if request.method == 'POST':
        datos = datos_json(request)
        try:
            enviar_mensaje(request.user, datos.get('mensaje'), datos.get('clave_envio'))
        except ErrorChat as exc:
            return error(str(exc), exc.estado)
    return JsonResponse(chat_json(request.user))
