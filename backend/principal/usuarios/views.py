from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from principal.http import acceso, datos_json, error
from .models import Perfil
from .retencion import DIAS_RETENCION, VERSION_TERMINOS, politica_json

User = get_user_model()


def usuario_json(usuario):
    perfil = getattr(usuario, 'perfil', None)
    aceptados = bool(perfil and perfil.terminos_aceptados_en and perfil.terminos_version == VERSION_TERMINOS)
    return {
        'id': usuario.pk,
        'username': usuario.username,
        'email': usuario.email,
        'nombre': usuario.first_name,
        'es_admin': usuario.is_staff,
        'terminos_aceptados': aceptados,
        'retencion_dias': DIAS_RETENCION if aceptados else None,
        'version_terminos': perfil.terminos_version if aceptados else None,
    }


@ensure_csrf_cookie
@acceso(['GET'], publico=True)
def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@acceso(['GET'], publico=True)
def terminos(request):
    return JsonResponse(politica_json())


@acceso(['GET'], publico=True)
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'usuario': None})
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    perfil.ultima_actividad = timezone.now()
    perfil.conectado = True
    perfil.save(update_fields=['ultima_actividad', 'conectado'])
    return JsonResponse({'usuario': usuario_json(request.user)})


@acceso(['POST'], publico=True)
def registro(request):
    datos = datos_json(request)
    if datos.get('acepta_terminos') is not True:
        return error('Debes aceptar los términos y la eliminación automática de los mensajes a los 30 días para crear tu cuenta.')
    if datos.get('version_terminos') != VERSION_TERMINOS:
        return error('Los términos han cambiado. Actualiza la página y vuelve a leerlos antes de aceptar.')
    email = str(datos.get('email', '')).strip().lower()
    password = datos.get('password', '')
    nombre = str(datos.get('nombre', '')).strip()
    try:
        validate_email(email)
    except ValidationError:
        return error('Escribe una dirección de Gmail válida.')
    if not email.endswith('@gmail.com') or len(email) > 150:
        return error('Crea tu cuenta con una dirección @gmail.com.')
    if not isinstance(password, str) or not password or len(password) > 128:
        return error('La contraseña debe tener entre 8 y 128 caracteres.')
    if len(nombre) > 150:
        return error('El nombre puede tener hasta 150 caracteres.')
    usuario = User(username=email, email=email, first_name=nombre)
    try:
        validate_password(password, user=usuario)
    except ValidationError as exc:
        return error(' '.join(exc.messages))
    try:
        with transaction.atomic():
            usuario.set_password(password)
            usuario.save()
            ahora = timezone.now()
            Perfil.objects.create(
                usuario=usuario, ultima_actividad=ahora, conectado=True,
                terminos_version=VERSION_TERMINOS, terminos_aceptados_en=ahora,
            )
    except IntegrityError:
        return error('Ya existe una cuenta con ese Gmail. Inicia sesión.', 409)
    login(request, usuario)
    return JsonResponse({'usuario': usuario_json(usuario)}, status=201)


@acceso(['POST'], publico=True)
def iniciar_sesion(request):
    datos = datos_json(request)
    # El estudiante entra con su Gmail y el administrador local con "admin".
    identificador = datos.get('username', datos.get('email', ''))
    password = datos.get('password', '')
    if not isinstance(identificador, str) or not isinstance(password, str):
        return error('Usuario o contraseña incorrectos.', 401)
    identificador = identificador.strip().lower()
    if not identificador or len(identificador) > 150 or len(password) > 128:
        return error('Usuario o contraseña incorrectos.', 401)
    # Límite local de intentos fallidos; no se guardan contraseñas en texto plano.
    clave = 'login:' + request.META.get('REMOTE_ADDR', '') + ':' + identificador
    intentos = cache.get(clave, 0)
    if intentos >= 10:
        return error('Hubo demasiados intentos. Espera 15 minutos y vuelve a intentar.', 429)
    usuario = authenticate(request, username=identificador, password=password)
    if usuario is None:
        cache.set(clave, intentos + 1, 900)
        return error('Usuario o contraseña incorrectos.', 401)
    cache.delete(clave)
    login(request, usuario)
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    perfil.ultima_actividad = timezone.now()
    perfil.conectado = True
    perfil.save(update_fields=['ultima_actividad', 'conectado'])
    return JsonResponse({'usuario': usuario_json(usuario)})


@acceso(['POST'])
def cerrar_sesion(request):
    Perfil.objects.filter(usuario=request.user).update(conectado=False)
    logout(request)
    return JsonResponse({'usuario': None})
