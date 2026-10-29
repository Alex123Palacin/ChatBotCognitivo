"""Exportación de frecuencias declaradas; no calcula intensidad ni un puntaje total."""
from datetime import datetime
from io import BytesIO
from math import ceil
import re
from zoneinfo import ZoneInfo

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ml.analisis import INDICADORES
from .indicadores import datos_indicadores
from .estudio import muestra_actual

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
    datos = datos_indicadores(usuarios, ahora)
    muestra = muestra_actual()
    periodo = (f'Mensajes del {hora_lima(muestra.inicio)} al {hora_lima(muestra.fin)} (fin exclusivo), hora de Lima. '
               'Sin dividir en semanas ni suponer una comparación inicial/final.' if muestra else
               'Actividad disponible hasta la fecha de exportación, sin dividir en semanas ni suponer una comparación inicial/final.')

    libro = Workbook()
    libro.remove(libro.active)
    libro.properties.creator = 'Chatbot Cognitivo'
    libro.properties.title = 'Frecuencias declaradas por indicador'
    columnas = [('ID estudiante', 20), ('Usuario', 25)]
    columnas.extend((f'Actividad · {meta["nombre"]}', 25) for meta in INDICADORES.values())
    resultados = crear_hoja(libro, 'Resultados', columnas)
    resultados.freeze_panes = 'C2'
    resultados.row_dimensions[1].height = 60
    ficha = crear_hoja(libro, 'Ficha', [('Campo', 31), ('Descripción', 115)])
    ficha.freeze_panes = 'A2'
    for fila in [
        ('Documento', 'Frecuencias declaradas por indicador · versión 3'),
        ('Exportado', hora_lima(ahora)),
        ('Periodo', periodo),
        ('Escala', '1 = Nunca; 2 = Rara vez; 3 = Algunas veces; 4 = Casi siempre; 5 = Siempre.'),
        ('Fuente', 'Frecuencias explícitas del estudiante vinculadas a un indicador y a un contexto temporal inequívoco. También se admite una respuesta tras una pregunta inequívoca del chatbot, en la misma sesión y dentro de dos horas. Se conservan las expresiones del estudiante; no se adivinan frecuencias.'),
        ('Dificultades', 'Sobrecarga, presión del tiempo y síntomas: mayor valor significa una dificultad relatada con mayor frecuencia.'),
        ('Afrontamiento', 'Planificación, automotivación y búsqueda de soporte: mayor valor significa mayor frecuencia de uso del recurso, no más estrés.'),
        ('Sin información', 'No hay una frecuencia inequívoca, hay relatos contradictorios, faltan mensajes o quedan análisis pendientes. No equivale a Nunca ni a cero estrés.'),
        ('Alcance', 'Registro descriptivo de frecuencia, sin suma global ni clasificación de estrés bajo, medio o alto. No es una escala validada de intensidad, un diagnóstico ni una prueba de eficacia.'),
        ('Identificadores', 'ID interno y nombre de usuario. No se incluyen nombres personales, correos, contraseñas ni conversaciones.'),
    ]:
        agregar(ficha, fila)
    if muestra:
        agregar(ficha, ('Selección', f'Muestra aleatoria fija de {muestra.tamano} estudiantes entre {len(muestra.poblacion_ids)}; fecha de selección: {hora_lima(muestra.creada)}. La descarga contiene los estudiantes solicitados dentro de esa muestra.'))
        agregar(ficha, ('Ventana de estudio', f'{hora_lima(muestra.inicio)} a {hora_lima(muestra.fin)} · America/Lima.'))
    demos = []
    for usuario in usuarios:
        codigo = f'Estudiante {usuario.pk}'
        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.origen_datos == 'demostracion':
            demos.append(codigo)
        fila = [codigo, usuario.username]
        fila.extend(datos[usuario.pk]['frecuencias'][indicador] for indicador in INDICADORES)
        agregar(resultados, fila)
    if demos:
        agregar(ficha, ('Tipo de datos', 'Demostración: ' + ', '.join(demos) + '. Sus relatos fueron generados para comprobar el sistema; no son observaciones de participantes de investigación.'))
    for hoja in libro:
        hoja.auto_filter.ref = hoja.dimensions
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
