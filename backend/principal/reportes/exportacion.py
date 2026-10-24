"""Descarga de evidencia registrada; no convierte conversaciones a puntajes SISCO."""
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from math import ceil
import re
from zoneinfo import ZoneInfo

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from chat.models import Mensaje
from ml.analisis import DIMENSIONES, INDICADORES, sintetizar_indicador
from sesiones.models import SesionSemanal
from .models import Evidencia

LIMA = ZoneInfo('America/Lima')
SENALES = {'dificultad': 'Dificultad expresada', 'recurso': 'Recurso de afrontamiento', 'ausencia_explicita': 'Ausencia expresada'}
CONTROL_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def hora_lima(fecha):
    # Excel no conserva zonas horarias: la ficha identifica la zona de todas las fechas.
    return fecha.astimezone(LIMA).replace(tzinfo=None) if fecha else None


def origen(usuario):
    perfil = getattr(usuario, 'perfil', None)
    return 'Demostración: personaje y relatos ficticios' if perfil and perfil.origen_datos == 'demostracion' else 'Interacción registrada'


def crear_hoja(libro, nombre, columnas):
    hoja = libro.create_sheet(nombre)
    hoja.append([c[0] for c in columnas])
    hoja.sheet_view.showGridLines = False
    hoja.freeze_panes = 'C2' if len(columnas) > 2 else 'A2'
    for indice, (_, ancho) in enumerate(columnas, 1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho
    for celda in hoja[1]:
        celda.fill = PatternFill('solid', fgColor='183653')
        celda.font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
        celda.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    hoja.row_dimensions[1].height = 34
    return hoja


def agregar(hoja, valores):
    hoja.append(valores)
    for celda in hoja[hoja.max_row]:
        if isinstance(celda.value, str):
            # Las conversaciones son texto, incluso si empiezan con =, +, - o @.
            celda.value = CONTROL_XML.sub('', celda.value)[:32767]
            celda.data_type = 's'
        if isinstance(celda.value, datetime):
            celda.number_format = 'dd/mm/yyyy hh:mm'
        celda.font = Font(name='Calibri', size=11, color='24374A')
        celda.alignment = Alignment(vertical='top', wrap_text=True)
        if hoja.max_row % 2 == 0:
            celda.fill = PatternFill('solid', fgColor='F0F5FA')
    lineas = max((sum(max(1, ceil(len(linea) / max(8, hoja.column_dimensions[c.column_letter].width - 3))) for linea in str(c.value or '').split('\n')) for c in hoja[hoja.max_row]), default=1)
    hoja.row_dimensions[hoja.max_row].height = min(409, max(30, lineas * 15 + 10))


def estado_periodo(sesion, mensajes, ahora):
    if not sesion:
        return 'Semana no registrada'
    if ahora < sesion.inicio:
        return 'Semana no iniciada'
    pendientes = sum(m.analisis_estado != 'listo' for m in mensajes)
    if not mensajes:
        return 'Sin mensajes' if ahora >= sesion.fin else 'En curso, sin mensajes'
    if pendientes:
        return f'Análisis pendiente: {pendientes} mensajes'
    return 'Finalizada, análisis disponible' if ahora >= sesion.fin else 'En curso, análisis provisional'


def descripcion(sesion, mensajes, evidencias, indicador, ahora):
    estado = estado_periodo(sesion, mensajes, ahora)
    items = [e for e in evidencias if e.indicador == indicador]
    if not items:
        return estado, 'Sin evidencia suficiente', '', ''
    senales = ' / '.join(SENALES[s] for s in SENALES if any(e.senal == s for e in items))
    conclusion = sintetizar_indicador([{'senal': e.senal, 'observacion': e.observacion} for e in items])
    citas = '\n'.join(f'{e.mensaje.fecha.astimezone(LIMA):%d/%m}: {e.cita}' for e in items)
    return estado, senales, conclusion, citas


def crear_excel(usuarios, ahora=None):
    ahora = ahora or timezone.now()
    ids = [u.pk for u in usuarios]
    mensajes = list(Mensaje.objects.filter(usuario_id__in=ids, fecha__lte=ahora).order_by('fecha', 'id')[:20001])
    if len(mensajes) > 20000:
        raise ValueError('La selección supera 20 000 mensajes. Descarga un grupo más pequeño.')
    sesiones = list(SesionSemanal.objects.filter(usuario_id__in=ids).order_by('numero'))
    por_sesion = {s.pk: s for s in sesiones}
    mensajes = [m for m in mensajes if m.sesion_id in por_sesion and por_sesion[m.sesion_id].usuario_id == m.usuario_id and por_sesion[m.sesion_id].inicio <= m.fecha < por_sesion[m.sesion_id].fin]
    por_id = {m.pk: m for m in mensajes if m.remitente == 'usuario'}
    evidencias = list(Evidencia.objects.filter(mensaje_id__in=por_id).order_by('mensaje__fecha', 'pk')[:60001])
    if len(evidencias) > 60000:
        raise ValueError('La selección tiene demasiadas evidencias. Descarga un grupo más pequeño.')
    evidencias = [e for e in evidencias if por_id[e.mensaje_id].analisis_estado == 'listo' and e.indicador in INDICADORES and e.senal in SENALES and e.cita.strip() and e.cita in por_id[e.mensaje_id].contenido]
    ms, es = defaultdict(list), defaultdict(list)
    for mensaje in por_id.values():
        ms[mensaje.sesion_id].append(mensaje)
    for evidencia in evidencias:
        evidencia.mensaje = por_id[evidencia.mensaje_id]
        es[evidencia.mensaje.sesion_id].append(evidencia)

    libro = Workbook()
    libro.remove(libro.active)
    libro.properties.creator = 'Chatbot Cognitivo'
    libro.properties.title = 'Evaluación conversacional inicial y final'
    ficha = crear_hoja(libro, 'Ficha', [('Campo', 30), ('Descripción', 110)])
    for fila in [
        ('Documento', 'Evaluación conversacional inicial y final · versión 1'),
        ('Exportado', hora_lima(ahora)),
        ('Zona horaria', 'America/Lima (UTC-05:00), todas las fechas del archivo'),
        ('Población prevista', 'Estudiantes de quinto de secundaria de colegio'),
        ('Inicio y cierre', 'Inicio = semana 1; cierre = semana 4. Se incluyen todos sus mensajes disponibles al descargar. La semana 1 no es una medición anterior al uso del chatbot.'),
        ('Método', 'Análisis automático cualitativo por siete indicadores de las tres dimensiones del proyecto. Las observaciones se respaldan con citas literales del estudiante.'),
        ('Alcance', 'No se aplicó el cuestionario SISCO: este archivo no produce su pretest/postest, escala 1–5, baremos, diagnósticos ni prueba de eficacia. La comparación describe relatos de dos periodos.'),
        ('Señales', 'Dificultad expresada; recurso de afrontamiento; ausencia expresada. Pueden coexistir. Una ausencia requiere una negación explícita, no falta de citas.'),
        ('Información faltante', 'Sin mensajes, análisis pendiente y sin evidencia son estados distintos. No equivalen a cero estrés ni se rellenan con valores inventados.'),
        ('Lectura', 'Comparación contrasta semanas 1 y 4. Semanas incluye los cuatro periodos. Evidencias y Conversaciones permiten revisar cada fuente por su identificador.'),
        ('Actividad', 'Los recuentos representan mensajes y días con actividad; no son puntuaciones de estrés ni minutos de conversación continua.'),
        ('Procedencia', 'Consultar Origen en Estudiantes y Comparación. Los registros de demostración son ficticios y no constituyen participantes ni resultados empíricos de la tesis.'),
        ('Acceso', 'Exportación exclusiva del administrador. Contiene relatos personales; no incluye contraseñas ni correos.'),
    ]:
        agregar(ficha, fila)
    estudiantes = crear_hoja(libro, 'Estudiantes', [('Código', 15), ('Nombre', 32), ('Origen', 49), ('Primer mensaje', 22), ('Último mensaje', 22), ('Mensajes del estudiante', 18), ('Días con mensajes', 18)])
    comparacion = crear_hoja(libro, 'Comparación', [('Código', 15), ('Nombre', 30), ('Origen', 49), ('Dimensión', 29), ('Indicador', 27), ('Estado inicial · S1', 34), ('Señales iniciales', 35), ('Observación inicial', 64), ('Citas iniciales', 70), ('Estado final · S4', 34), ('Señales finales', 35), ('Observación final', 64), ('Citas finales', 70)])
    semanas = crear_hoja(libro, 'Semanas', [('Código', 15), ('Semana', 12), ('Inicio', 22), ('Fin exclusivo', 22), ('Estado', 36), ('Mensajes del estudiante', 18), ('Analizados', 16), ('Pendientes', 16), ('Días con mensajes', 18), ('Indicadores con citas (de 7)', 21)])
    fuentes = crear_hoja(libro, 'Evidencias', [('Código', 15), ('Semana', 12), ('Fecha', 22), ('Dimensión', 29), ('Indicador', 27), ('Señal', 30), ('Cita literal', 75), ('Observación del sistema', 70), ('ID mensaje', 40)])
    conversaciones = crear_hoja(libro, 'Conversaciones', [('Código', 15), ('Semana', 12), ('Fecha', 22), ('Remitente', 18), ('Contenido', 100), ('Análisis', 20), ('ID mensaje', 40), ('En respuesta a', 40)])
    for usuario in usuarios:
        codigo = f'EST-{usuario.pk:05d}'
        propias = {s.numero: s for s in sesiones if s.usuario_id == usuario.pk}
        propios = [m for m in por_id.values() if m.usuario_id == usuario.pk]
        agregar(estudiantes, [codigo, usuario.first_name, origen(usuario), hora_lima(min((m.fecha for m in propios), default=None)), hora_lima(max((m.fecha for m in propios), default=None)), len(propios), len({m.fecha.astimezone(LIMA).date() for m in propios})])
        for indicador, metadata in INDICADORES.items():
            periodos = []
            for numero in (1, 4):
                sesion = propias.get(numero)
                periodos.extend(descripcion(sesion, ms[sesion.pk] if sesion else [], es[sesion.pk] if sesion else [], indicador, ahora))
            agregar(comparacion, [codigo, usuario.first_name, origen(usuario), DIMENSIONES[metadata['dimension']], metadata['nombre'], *periodos])
        for numero in range(1, 5):
            sesion = propias.get(numero)
            registros = ms[sesion.pk] if sesion else []
            analizados = sum(m.analisis_estado == 'listo' for m in registros)
            agregar(semanas, [codigo, numero, hora_lima(sesion.inicio) if sesion else None, hora_lima(sesion.fin) if sesion else None, estado_periodo(sesion, registros, ahora), len(registros), analizados, len(registros) - analizados, len({m.fecha.astimezone(LIMA).date() for m in registros}), len({e.indicador for e in es[sesion.pk]}) if sesion else 0])
        for e in (e for e in evidencias if e.mensaje.usuario_id == usuario.pk):
            metadata = INDICADORES[e.indicador]
            agregar(fuentes, [codigo, por_sesion[e.mensaje.sesion_id].numero, hora_lima(e.mensaje.fecha), DIMENSIONES[metadata['dimension']], metadata['nombre'], SENALES[e.senal], e.cita, e.observacion, str(e.mensaje_id)])
        for m in (m for m in mensajes if m.usuario_id == usuario.pk):
            agregar(conversaciones, [codigo, por_sesion[m.sesion_id].numero, hora_lima(m.fecha), 'Estudiante' if m.remitente == 'usuario' else 'Chatbot', m.contenido, m.analisis_estado if m.remitente == 'usuario' else 'No corresponde', str(m.pk), str(m.respuesta_a_id) if m.respuesta_a_id else ''])
    for hoja in libro:
        hoja.auto_filter.ref = hoja.dimensions
    libro.active = 2
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
