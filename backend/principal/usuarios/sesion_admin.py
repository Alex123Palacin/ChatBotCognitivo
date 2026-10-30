"""La actividad humana renueva el acceso; las consultas automáticas no."""
import secrets
from django.contrib.auth import logout
from django.utils import timezone

SEGUNDOS_INACTIVIDAD = 600


def preparar_sesion_admin(request):
    token = secrets.token_urlsafe(32)
    request.session['admin_pestana'] = token
    renovar_sesion_admin(request)
    return token


def renovar_sesion_admin(request):
    request.session['admin_actividad'] = timezone.now().timestamp()
    request.session.set_expiry(SEGUNDOS_INACTIVIDAD)


def sesion_admin_valida(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return True
    token = request.session.get('admin_pestana')
    # Una sesión heredada nunca recibe un plazo nuevo por consultar la API.
    if not token:
        inicio = request.user.last_login
        if inicio and (timezone.now() - inicio).total_seconds() < SEGUNDOS_INACTIVIDAD:
            return True
        logout(request)
        return False
    ultima = request.session.get('admin_actividad', 0)
    if timezone.now().timestamp() - ultima >= SEGUNDOS_INACTIVIDAD:
        logout(request)
        return False
    recibido = request.headers.get('X-Admin-Pestana', '')
    # Una pestaña sin el identificador no invalida la pestaña autorizada.
    return secrets.compare_digest(token, recibido)
