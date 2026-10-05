import json
import re
from uuid import uuid4

from django.core.cache import cache
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from ml.conversacion import nuevo_estado, procesar
from ml.ollama import ErrorModelo

TIEMPO_SESION = 7200


@require_GET
@never_cache
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
@never_cache
def chat(request):
    if len(request.body) > 12000:
        return JsonResponse({"error": "El mensaje es demasiado largo."}, status=400)
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            raise ValueError()
        mensaje = datos.get("mensaje", "")
        opcion = datos.get("opcion")
        pregunta_id = datos.get("pregunta_id")
        sesion_id = datos.get("sesion_id")
        if not isinstance(mensaje, str) or len(mensaje) > 2000:
            raise ValueError()
        if opcion is not None and not isinstance(opcion, str):
            raise ValueError()
        if pregunta_id is not None and not isinstance(pregunta_id, str):
            raise ValueError()
        if not mensaje.strip() and opcion is None:
            raise ValueError()
        if sesion_id is not None and (not isinstance(sesion_id, str) or not re.fullmatch(r'[0-9a-f]{32}', sesion_id)):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Envía un mensaje de 1 a 2000 caracteres o una opción válida."}, status=400)

    sesion_id = sesion_id or uuid4().hex
    clave = "chat:" + sesion_id
    if not cache.add(clave + ":ocupado", True, timeout=240):
        return JsonResponse({"error": "Ya hay una respuesta en curso. Espera un momento."}, status=409)
    try:
        estado = cache.get(clave)
        if datos.get("sesion_id") and estado is None:
            return JsonResponse({"error": "La conversación caducó o el servidor se reinició. Inicia un nuevo chat."}, status=410)
        estado = estado or nuevo_estado()
        salida = procesar(estado, mensaje.strip(), opcion, pregunta_id)
        if cache.get(clave + ":eliminado"):
            return JsonResponse({"error": "Esta conversación fue eliminada."}, status=410)
        cache.set(clave, estado, timeout=TIEMPO_SESION)
        return JsonResponse({"sesion_id": sesion_id, **salida})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except ErrorModelo as error:
        return JsonResponse({"error": str(error)}, status=503)
    finally:
        cache.delete(clave + ":ocupado")


@require_http_methods(["DELETE"])
@never_cache
def borrar_chat(request, sesion_id):
    cache.set("chat:" + sesion_id + ":eliminado", True, timeout=TIEMPO_SESION)
    cache.delete("chat:" + sesion_id)
    return JsonResponse({"eliminada": True})
