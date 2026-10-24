from datetime import timedelta

from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Min, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from principal.http import acceso, error
from sesiones.models import SesionSemanal
from sesiones.services import sesion_json
from .models import ReporteSemanal
from .services import NOTA_METODO, dimensiones_json, resumen_json, reporte_actual_json

User = get_user_model()


def alumno_json(usuario, ahora=None):
    ahora = ahora or timezone.now()
    perfil = getattr(usuario, 'perfil', None)
    ultima = perfil.ultima_actividad if perfil else None
    semana = usuario.semanas.filter(inicio__lte=ahora, fin__gt=ahora).first()
    actividad = usuario.mensajes_chat.filter(remitente='usuario').annotate(dia=TruncDate('fecha')).aggregate(primero=Min('fecha'), ultimo=Max('fecha'), dias=Count('dia', distinct=True), cantidad=Count('id'), analizados=Count('id', filter=Q(analisis_estado='listo')))
    return {'id': usuario.pk, 'nombre': usuario.first_name, 'email': usuario.email, 'ultima_actividad': ultima.isoformat() if ultima else None, 'en_linea': bool(perfil and perfil.conectado and ultima and ultima >= ahora - timedelta(minutes=5)), 'semana_actual': semana.numero if semana else None, 'reportes_total': ReporteSemanal.objects.filter(sesion__usuario=usuario).count(), 'primer_mensaje': actividad['primero'].isoformat() if actividad['primero'] else None, 'ultimo_mensaje': actividad['ultimo'].isoformat() if actividad['ultimo'] else None, 'inicio_programa': perfil.inicio_programa.isoformat() if perfil and perfil.inicio_programa else None, 'dias_conversacion': actividad['dias'], 'mensajes_estudiante': actividad['cantidad'], 'mensajes_analizados': actividad['analizados'], 'analisis_pendientes': actividad['cantidad'] - actividad['analizados']}


@acceso(['GET'], administrador=True)
def alumnos(request):
    ahora = timezone.now()
    return JsonResponse({'alumnos': [alumno_json(u, ahora) for u in User.objects.filter(is_staff=False).select_related('perfil').order_by('first_name', 'email')]})


@acceso(['GET'], administrador=True)
def alumno(request, alumno_id):
    usuario = User.objects.filter(pk=alumno_id, is_staff=False).select_related('perfil').first()
    if not usuario:
        return error('No se encontró al estudiante.', 404)
    ahora = timezone.now()
    sesiones = list(SesionSemanal.objects.filter(usuario=usuario).select_related('reporte'))
    reportes = ReporteSemanal.objects.filter(sesion__usuario=usuario).select_related('sesion')
    actual = next((s for s in sesiones if s.inicio <= ahora < s.fin), None)
    if actual is None and sesiones and ahora >= sesiones[-1].fin:
        actual = sesiones[-1]
    return JsonResponse({'alumno': alumno_json(usuario, ahora), 'sesiones': [sesion_json(s, ahora) for s in sesiones], 'reportes': [resumen_json(r) for r in reportes], 'reporte_actual': reporte_actual_json(actual, ahora) if actual else None})


@acceso(['GET'], administrador=True)
def reporte(request, reporte_id):
    reporte = ReporteSemanal.objects.filter(pk=reporte_id).select_related('sesion__usuario__perfil').first()
    if not reporte:
        return error('No se encontró el reporte.', 404)
    return JsonResponse({**resumen_json(reporte), 'nota': NOTA_METODO, 'alumno': alumno_json(reporte.sesion.usuario), 'dimensiones': dimensiones_json(reporte)})


@acceso(['GET'], administrador=True)
def exportar(request):
    from .exportacion import crear_excel
    valores = request.GET.get('alumnos', '').split(',')
    if not 1 <= len(valores) <= 100 or any(not v.isascii() or not v.isdecimal() or len(v) > 10 for v in valores):
        raise ValueError('Selecciona entre 1 y 100 estudiantes para descargar.')
    ids = {int(v) for v in valores}
    usuarios = list(User.objects.filter(pk__in=ids, is_staff=False, is_superuser=False).select_related('perfil').order_by('first_name', 'pk'))
    if len(usuarios) != len(ids):
        return error('No se encontró alguno de los estudiantes seleccionados.', 404)
    respuesta = HttpResponse(crear_excel(usuarios), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    fecha = timezone.localdate().isoformat()
    respuesta['Content-Disposition'] = f'attachment; filename="evaluacion-inicial-final-{fecha}.xlsx"'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta
