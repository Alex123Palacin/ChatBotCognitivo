"""Exportación de frecuencias declaradas; no calcula intensidad ni un puntaje total."""
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from math import ceil
import re
from zoneinfo import ZoneInfo

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from chat.models import Mensaje
from ml.analisis import INDICADORES
from sesiones.models import SesionSemanal
from .models import Evidencia
from .frecuencias import frecuencia_periodo

LIMA = ZoneInfo('America/Lima')
CONTROL_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def hora_lima(fecha):
    # Excel no conserva zonas horarias: la ficha identifica la zona de todas las fechas.
    return fecha.astimezone(LIMA).replace(tzinfo=None) if fecha else None


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


def crear_excel(usuarios, ahora=None):
    ahora = ahora or timezone.now()
    usuarios = sorted(usuarios, key=lambda usuario: usuario.pk)
    ids = [u.pk for u in usuarios]
    sesiones = {s.pk: s for s in SesionSemanal.objects.filter(usuario_id__in=ids, numero__in=(1, 4))}
    mensajes = list(Mensaje.objects.filter(usuario_id__in=ids, sesion_id__in=sesiones, fecha__lte=ahora).order_by('fecha', 'pk')[:20001])
    if len(mensajes) > 20000:
        raise ValueError('La selección supera 20 000 mensajes. Descarga un grupo más pequeño.')
    mensajes = [m for m in mensajes if sesiones[m.sesion_id].usuario_id == m.usuario_id and sesiones[m.sesion_id].inicio <= m.fecha < sesiones[m.sesion_id].fin]
    anteriores = {}
    relatos = {m.pk: m for m in mensajes if m.remitente == 'usuario'}
    for mensaje in mensajes:
        previo = anteriores.get((mensaje.usuario_id, mensaje.sesion_id))
        padre = relatos.get(previo.respuesta_a_id) if previo else None
        if previo and padre and previo.remitente == 'asistente' and padre.usuario_id == mensaje.usuario_id and padre.sesion_id == mensaje.sesion_id and padre.fecha <= previo.fecha and timedelta(0) <= mensaje.fecha - previo.fecha <= timedelta(hours=2):
            mensaje._pregunta_frecuencia = previo.contenido
        anteriores[(mensaje.usuario_id, mensaje.sesion_id)] = mensaje
    mensajes = {m.pk: m for m in mensajes if m.remitente == 'usuario'}
    por_sesion, evidencias = defaultdict(list), defaultdict(list)
    for mensaje in mensajes.values():
        por_sesion[mensaje.sesion_id].append(mensaje)
    candidatas = list(Evidencia.objects.filter(mensaje_id__in=mensajes).order_by('mensaje__fecha', 'pk')[:60001])
    if len(candidatas) > 60000:
        raise ValueError('La selección tiene demasiadas evidencias. Descarga un grupo más pequeño.')
    for evidencia in candidatas:
        evidencia.mensaje = mensajes[evidencia.mensaje_id]
        evidencias[evidencia.mensaje.sesion_id].append(evidencia)

    libro = Workbook()
    libro.remove(libro.active)
    libro.properties.creator = 'Chatbot Cognitivo'
    libro.properties.title = 'Frecuencias declaradas por indicador'
    columnas = [('ID estudiante', 20)]
    for periodo in ('Inicial · S1', 'Final · S4'):
        columnas.extend((f'{periodo} · {meta["nombre"]}', 25) for meta in INDICADORES.values())
    resultados = crear_hoja(libro, 'Resultados', columnas)
    resultados.freeze_panes = 'B2'
    resultados.row_dimensions[1].height = 60
    ficha = crear_hoja(libro, 'Ficha', [('Campo', 31), ('Descripción', 115)])
    ficha.freeze_panes = 'A2'
    for fila in [
        ('Documento', 'Frecuencias declaradas por indicador · versión 2'),
        ('Exportado', hora_lima(ahora)),
        ('Periodo', 'Inicial = semana 1; final = semana 4. Son periodos de conversación, no una medición anterior al uso del sistema.'),
        ('Escala', '1 = Nunca; 2 = Rara vez; 3 = Algunas veces; 4 = Casi siempre; 5 = Siempre.'),
        ('Fuente', 'Expresiones literales del estudiante vinculadas a un indicador y a esta semana. También se acepta una respuesta de frecuencia tras una pregunta semanal inequívoca del chatbot, en la misma sesión y dentro de dos horas. No se adivinan frecuencias.'),
        ('Dificultades', 'Sobrecarga, presión del tiempo y síntomas: mayor valor significa una dificultad relatada con mayor frecuencia.'),
        ('Afrontamiento', 'Planificación, automotivación y búsqueda de soporte: mayor valor significa mayor frecuencia de uso del recurso, no más estrés.'),
        ('Sin información', 'No hay una frecuencia inequívoca, hay relatos contradictorios, faltan mensajes, quedan análisis pendientes o la semana todavía no finaliza. No equivale a Nunca ni a cero estrés.'),
        ('Alcance', 'Registro descriptivo de frecuencia, sin suma global ni clasificación de estrés bajo, medio o alto. No es una escala validada de intensidad, un diagnóstico ni una prueba de eficacia.'),
        ('Identificadores', 'Se usa el ID interno del estudiante. Este archivo no incluye nombres, correos, contraseñas ni conversaciones.'),
    ]:
        agregar(ficha, fila)
    demos = []
    for usuario in usuarios:
        codigo = f'Estudiante {usuario.pk}'
        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.origen_datos == 'demostracion':
            demos.append(codigo)
        fila = [codigo]
        for numero in (1, 4):
            sesion = next((s for s in sesiones.values() if s.usuario_id == usuario.pk and s.numero == numero), None)
            registros = por_sesion[sesion.pk] if sesion else []
            completo = bool(sesion and ahora >= sesion.fin and registros and all(m.analisis_estado == 'listo' for m in registros))
            fila.extend(frecuencia_periodo(evidencias[sesion.pk], indicador, registros) if completo else 'Sin información' for indicador in INDICADORES)
        agregar(resultados, fila)
    if demos:
        agregar(ficha, ('Tipo de datos', 'Demostración: ' + ', '.join(demos) + '. Sus relatos fueron generados para comprobar el sistema; no son observaciones de participantes de investigación.'))
    for hoja in libro:
        hoja.auto_filter.ref = hoja.dimensions
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
