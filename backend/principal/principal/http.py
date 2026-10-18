import json
from functools import wraps

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


def error(texto, estado=400):
    return JsonResponse({'error': texto}, status=estado)


def datos_json(request):
    try:
        datos = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Envía los datos como JSON válido.')
    if not isinstance(datos, dict):
        raise ValueError('Los datos deben ser un objeto JSON.')
    return datos


def acceso(metodos, administrador=False, estudiante=False, publico=False):
    def decorar(vista):
        @never_cache
        @wraps(vista)
        def ejecutar(request, *args, **kwargs):
            if request.method not in metodos:
                return error('Método no permitido.', 405)
            if not publico and not request.user.is_authenticated:
                return error('Inicia sesión para continuar.', 401)
            if administrador and not request.user.is_staff:
                return error('Solo el administrador puede consultar los reportes.', 403)
            if estudiante and request.user.is_staff:
                return error('Esta sección pertenece a los estudiantes.', 403)
            try:
                return vista(request, *args, **kwargs)
            except ValueError as exc:
                return error(str(exc))
        return ejecutar
    return decorar


@never_cache
def csrf_fallido(request, reason=''):
    return error('La sesión de seguridad venció. Actualiza la página y vuelve a intentarlo.', 403)


@acceso(['GET'], publico=True)
def salud(request):
    """Comprueba el servidor y la base sin consultar ni revelar datos personales."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return error('La base de datos no está disponible.', 503)
    return JsonResponse({'estado': 'ok'})
