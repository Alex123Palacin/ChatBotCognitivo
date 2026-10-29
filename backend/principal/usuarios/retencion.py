"""Política explícita para nuevos registros, sin inscribir datos históricos."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone


VERSION_ANTERIOR = 'conversaciones-30-dias-v1'
VERSION_TERMINOS = 'conversaciones-90-dias-acceso-v2'
# Conservar versiones anteriores cuando en el futuro se publique otra política.
VERSIONES_CON_RETENCION = (VERSION_ANTERIOR, VERSION_TERMINOS)
DIAS_RETENCION = 90
TEXTO_RETENCION = (
    'La conversación se almacena bajo tu nombre de usuario y se analiza para generar '
    'reportes orientativos que pueden consultar administradores autorizados. '
    'No constituye un diagnóstico. Tus mensajes nuevos se eliminarán automáticamente '
    'al cumplir 90 días desde tu último inicio de sesión correcto. Cada nuevo inicio '
    'de sesión reinicia ese plazo para los mensajes sujetos a esta política. '
    'También se retirarán las citas y los resúmenes '
    'derivados de los mensajes eliminados. Mi cuenta no se elimina por este plazo. '
    'Las copias de seguridad y los archivos que ya se hayan descargado tienen una '
    'gestión de conservación independiente.'
)


def politica_json():
    return {
        'version': VERSION_TERMINOS,
        'dias_retencion': DIAS_RETENCION,
        'texto': TEXTO_RETENCION,
        'alcance': 'mensajes_nuevos',
        'copias_seguridad': 'gestion_separada',
        'base_plazo': 'ultimo_inicio_sesion',
    }


def fecha_eliminacion(fecha, perfil):
    """Nunca asigna caducidad a cuentas o mensajes anteriores a la aceptación."""
    aceptacion = perfil.terminos_aceptados_en
    if perfil.terminos_version not in VERSIONES_CON_RETENCION or aceptacion is None:
        return None
    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    if fecha < aceptacion:
        return None
    if perfil.terminos_version == VERSION_ANTERIOR:
        return fecha + timedelta(days=30)
    acceso = perfil.usuario.last_login or aceptacion
    return max(acceso, aceptacion) + timedelta(days=DIAS_RETENCION)


def renovar_retencion(usuario):
    """Solo un login correcto renueva v2; me() y los latidos no lo renuevan."""
    from chat.models import Mensaje
    perfil = getattr(usuario, 'perfil', None)
    if perfil and perfil.terminos_version == VERSION_TERMINOS and perfil.terminos_aceptados_en:
        fecha = max(usuario.last_login or perfil.terminos_aceptados_en, perfil.terminos_aceptados_en)
        Mensaje.objects.filter(usuario=usuario, retencion_version=VERSION_TERMINOS,
                               eliminar_despues_de__isnull=False).update(eliminar_despues_de=fecha + timedelta(days=DIAS_RETENCION))


def mensajes_vencidos(ahora=None):
    from chat.models import Mensaje

    ahora = ahora or timezone.now()
    return (
        Mensaje.objects.filter(
            eliminar_despues_de__lte=ahora,
            retencion_version__in=VERSIONES_CON_RETENCION,
        )
        .filter(Q(retencion_version=VERSION_ANTERIOR)
                | Q(retencion_version=VERSION_TERMINOS, usuario__last_login__lte=ahora - timedelta(days=90))
                | Q(retencion_version=VERSION_TERMINOS, usuario__last_login__isnull=True,
                    usuario__perfil__terminos_aceptados_en__lte=ahora - timedelta(days=90)))
        .exclude(usuario__perfil__respuesta_hasta__gt=ahora)
        # La relación respuesta_a usa CASCADE. Una respuesta histórica sin plazo
        # no debe borrarse indirectamente al eliminar su mensaje padre.
        .exclude(
            Q(respuesta__isnull=False)
            & (Q(respuesta__eliminar_despues_de__isnull=True) | ~Q(respuesta__retencion_version__in=VERSIONES_CON_RETENCION))
        )
    )


@transaction.atomic
def limpiar_conversaciones(*, aplicar=False, ahora=None, limite=1000):
    """Borrado por lotes de datos elegibles; no imprime texto ni identificadores.

    Los perfiles heredados y los mensajes sin fecha de eliminación están fuera
    de la selección. No se alteran cuentas ni fechas de sesiones.
    """
    from chat.models import Mensaje
    from reportes.models import Evidencia, ReporteSemanal

    ahora = ahora or timezone.now()
    limite = max(1, min(int(limite), 10000))
    ids = list(mensajes_vencidos(ahora).order_by('eliminar_despues_de', 'id').values_list('id', flat=True)[:limite])
    seleccion = Mensaje.objects.filter(pk__in=ids)
    sesiones = list(seleccion.values_list('sesion_id', flat=True).distinct())
    resultado = {
        'aplicado': aplicar,
        'mensajes_vencidos': len(ids),
        'evidencias': Evidencia.objects.filter(mensaje_id__in=ids).count(),
        'reportes_derivados': ReporteSemanal.objects.filter(sesion_id__in=sesiones).count(),
        'mensajes_eliminados': 0,
    }
    if aplicar and ids:
        # Los resúmenes pueden conservar citas del texto vencido. Se retiran;
        # los mensajes vigentes conservan sus evidencias y pueden reanalizarse.
        ReporteSemanal.objects.filter(sesion_id__in=sesiones).delete()
        _, eliminados = seleccion.delete()
        resultado['mensajes_eliminados'] = eliminados.get('chat.Mensaje', 0)
    return resultado
