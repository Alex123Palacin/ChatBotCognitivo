"""Prepara un paquete portable y accesos privados sin abrir la base del proyecto.

Las anotaciones son estructuradas; no se atribuyen a una ejecución de Ollama.
La procedencia se conserva en los metadatos y en Perfil al importar.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timedelta
import hashlib
from itertools import combinations
import json
from pathlib import Path
import random
import secrets
import sys
import unicodedata
import uuid
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[2]
LIMA = ZoneInfo('America/Lima')
DIFICULTADES = ('sobrecarga_academica', 'presion_tiempo', 'sintomas_fisicos', 'sintomas_psicologicos')
RECURSOS = ('planificacion', 'automotivacion', 'busqueda_soporte')
DISTRIBUCION = {0: 4, 1: 32, 2: 36, 3: 36, 4: 28}
NOMBRES = (
    'Adriana', 'Alonso', 'Andrea', 'Andrés', 'Ángela', 'Anthony', 'Ariana', 'Bruno',
    'Camila', 'Carlos', 'Carolina', 'César', 'Claudia', 'Cristian', 'Daniela', 'Daniel',
    'Diana', 'Diego', 'Elena', 'Eduardo', 'Estefanía', 'Emilio', 'Fabiola', 'Fabricio',
    'Fernanda', 'Fernando', 'Fiorella', 'Franco', 'Gabriela', 'Gabriel', 'Gianella', 'Gonzalo',
    'Grecia', 'Guillermo', 'Isabel', 'Ignacio', 'Jimena', 'Joaquín', 'Josefina', 'Jorge',
    'Juliana', 'José', 'Kiara', 'Kevin', 'Lucía', 'Leonardo', 'Luana', 'Luis',
    'Mariana', 'Manuel', 'María Fernanda', 'Marco', 'Micaela', 'Matías', 'Milagros', 'Miguel',
    'Natalia', 'Nicolás', 'Nicole', 'Óscar', 'Paola', 'Pablo', 'Patricia', 'Piero',
    'Regina', 'Rafael', 'Renata', 'Renzo', 'Rocío', 'Ricardo', 'Romina', 'Rodrigo',
    'Salomé', 'Salvador', 'Samantha', 'Samuel', 'Sara', 'Santiago', 'Silvana', 'Sebastián',
    'Sofía', 'Sergio', 'Tamara', 'Thiago', 'Valentina', 'Tomás', 'Valeria', 'Víctor',
    'Vanessa', 'Walter', 'Victoria', 'Xavier', 'Ximena', 'Yahir', 'Yamila', 'Álvaro',
)
APELLIDOS = (
    'Aguilar', 'Alarcón', 'Alvarado', 'Arce', 'Arias', 'Ayala', 'Barrios', 'Benavides',
    'Bustamante', 'Cabrera', 'Cáceres', 'Calderón', 'Campos', 'Cárdenas', 'Carrasco', 'Castillo',
    'Castro', 'Chávez', 'Córdova', 'Cornejo', 'Cruz', 'Delgado', 'Díaz', 'Espinoza',
    'Fernández', 'Flores', 'Gamarra', 'García', 'Gómez', 'Gonzales', 'Guevara', 'Gutiérrez',
    'Herrera', 'Huamán', 'Jiménez', 'Lara', 'León', 'López', 'Lozano', 'Maldonado',
    'Medina', 'Mejía', 'Mendoza', 'Miranda', 'Molina', 'Montes', 'Morales', 'Moreno',
    'Navarro', 'Núñez', 'Ortega', 'Ortiz', 'Palacios', 'Paredes', 'Peña', 'Pérez',
    'Ponce', 'Quispe', 'Ramírez', 'Ramos', 'Reyes', 'Ríos', 'Rivera', 'Rojas',
    'Romero', 'Ruiz', 'Salas', 'Salazar', 'Sánchez', 'Sandoval', 'Silva', 'Soto',
    'Suárez', 'Tapia', 'Torres', 'Valdez', 'Vargas', 'Vásquez', 'Vega', 'Vera',
    'Vilca', 'Villanueva', 'Yupanqui', 'Zambrano',
)


def guardar_privado(ruta: Path, contenido: str | bytes):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + '.tmp')
    temporal.write_bytes(contenido.encode('utf-8') if isinstance(contenido, str) else contenido)
    temporal.chmod(0o600)
    temporal.replace(ruta)


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c))


def perfiles(fecha: date):
    """Distribución fija con combinaciones equilibradas y orden de listado mezclado."""
    rng = random.Random(f'actividad-{fecha.isoformat()}-136-v1')
    grados = [grado for grado, cantidad in DISTRIBUCION.items() for _ in range(cantidad)]
    rng.shuffle(grados)
    elecciones = {grado: list(combinations(DIFICULTADES, grado)) for grado in DISTRIBUCION}
    for valores in elecciones.values():
        rng.shuffle(valores)
    vistos = {grado: 0 for grado in DISTRIBUCION}
    nombres_usados = set()
    resultado = []
    for i, grado in enumerate(grados):
        nombre = NOMBRES[i % len(NOMBRES)]
        while True:
            primero, segundo = rng.sample(APELLIDOS, 2)
            completo = f'{nombre} {primero} {segundo}'
            if completo not in nombres_usados:
                nombres_usados.add(completo)
                break
        dificultad = list(elecciones[grado][vistos[grado] % len(elecciones[grado])])
        vistos[grado] += 1
        rng.shuffle(dificultad)
        # Afrontamiento se distribuye de manera independiente de las dificultades.
        cantidad_recursos = (i * 7 + grado) % 4
        recursos = rng.sample(RECURSOS, cantidad_recursos)
        sufijo = hashlib.sha256(f'{fecha.isoformat()}/{i}'.encode()).hexdigest()[:6]
        email = f'{normalizar(nombre.split()[0])}.{normalizar(primero)}.{sufijo}@example.com'
        resultado.append({'clave': f'a{i+1:03d}', 'nombre': completo, 'email': email,
                          'dificultades': dificultad, 'recursos': recursos,
                          'voz': ('breve', 'coloquial', 'detallista', 'serena')[rng.randrange(4)],
                          'contexto_idx': rng.randrange(10000)})
    return resultado


def accesos_privados(personas, salida: Path):
    ruta = salida / 'accesos_privados.json'
    if ruta.exists():
        guardados = json.loads(ruta.read_text(encoding='utf-8'))
        if [(p['clave'], p['email']) for p in guardados] != [(p['clave'], p['email']) for p in personas]:
            raise ValueError('La salida contiene accesos de otra configuración. Usa una carpeta distinta.')
        return {p['clave']: p for p in guardados}
    # El hasher se usa sin django.setup ni conexión a ninguna base de datos.
    from django.contrib.auth.hashers import PBKDF2PasswordHasher

    def crear(persona):
        hasher = PBKDF2PasswordHasher()
        password = 'C' + secrets.token_urlsafe(15) + '7!'
        return {'clave': persona['clave'], 'nombre': persona['nombre'], 'email': persona['email'],
                'password': password, 'password_hash': hasher.encode(password, hasher.salt())}

    cuentas = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for cuenta in executor.map(crear, personas):
            cuentas.append(cuenta)
            if len(cuentas) % 20 == 0:
                print(f'Accesos preparados: {len(cuentas)}/136', flush=True)
    guardar_privado(ruta, json.dumps(cuentas, ensure_ascii=False, indent=2) + '\n')
    return {p['clave']: p for p in cuentas}


def calendarizar(pares, fecha: date, indice: int, lote: str, clave: str):
    rng = random.Random(f'{lote}/{clave}/horas')
    base = datetime.combine(fecha, datetime.min.time(), LIMA).replace(hour=13)
    por_bloque = {i: [] for i in range(5)}
    for par in pares:
        por_bloque[par['bloque']].append(par)
    if any(not valores for valores in por_bloque.values()):
        raise ValueError('Cada conversación debe tener actividad en los cinco bloques.')
    mensajes = []
    for bloque, valores in por_bloque.items():
        # Actividad en ráfagas separadas: no son mensajes espaciados uniformemente.
        # Primer bloque inicia a las 13:00-13:09; último acaba a las 17:49-17:59.
        comienzo = base + timedelta(minutes=bloque * 60 + rng.randint(0, 9), seconds=rng.randint(0, 40))
        final = base + timedelta(minutes=bloque * 60 + rng.randint(46, 57), seconds=rng.randint(0, 40))
        if bloque == 4:
            final = base + timedelta(minutes=rng.randint(290, 299), seconds=rng.randint(0, 25))
        pesos = [rng.uniform(0.5, 1.5) for _ in range(max(1, len(valores)-1))]
        acumulado = 0.0
        for j, par in enumerate(valores):
            fraccion = acumulado / sum(pesos) if len(valores) > 1 else 0
            momento = comienzo + (final - comienzo) * fraccion
            momento = momento.replace(microsecond=0)
            turno = len(mensajes) // 2
            mid = uuid.uuid5(uuid.NAMESPACE_URL, f'chatcognitivo/{lote}/{clave}/{turno}/usuario')
            aid = uuid.uuid5(uuid.NAMESPACE_URL, f'chatcognitivo/{lote}/{clave}/{turno}/asistente')
            mensajes.append({'id': str(mid), 'remitente': 'usuario', 'contenido': par['usuario'],
                             'fecha': momento.isoformat(), 'respuesta_a': None,
                             'evidencias': par['evidencias']})
            respuesta = momento + timedelta(seconds=rng.randint(3, 18))
            mensajes.append({'id': str(aid), 'remitente': 'asistente', 'contenido': par['asistente'],
                             'fecha': respuesta.isoformat(), 'respuesta_a': str(mid), 'evidencias': []})
            if j < len(pesos):
                acumulado += pesos[j]
    return mensajes


def preparar(fecha: date, salida: Path):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    from herramientas.carga_actividad.dialogos import construir_dialogo

    salida.mkdir(parents=True, exist_ok=True)
    lote = f'actividad-{fecha:%Y%m%d}-136-v1'
    personas = perfiles(fecha)
    accesos = accesos_privados(personas, salida)
    inicio = datetime.combine(fecha, datetime.min.time(), LIMA).replace(hour=13)
    datos = {'schema': 'chatcognitivo.actividad.v1', 'lote': lote, 'fecha': fecha.isoformat(),
             'zona_horaria': 'America/Lima', 'ventana_inicio': inicio.isoformat(),
             'ventana_fin': (inicio + timedelta(hours=5)).isoformat(), 'origen': 'demostracion',
             'analisis_metodo': 'anotacion_estructurada_v1', 'cuentas': []}
    auditoria = []
    for i, persona in enumerate(personas):
        rng = random.Random(f'{lote}/{persona["clave"]}/dialogo')
        pares = construir_dialogo(i, persona, rng)
        mensajes = calendarizar(pares, fecha, i, lote, persona['clave'])
        primero = datetime.fromisoformat(mensajes[0]['fecha'])
        datos['cuentas'].append({'clave': persona['clave'], 'nombre': persona['nombre'],
                                 'email': persona['email'], 'password_hash': accesos[persona['clave']]['password_hash'],
                                 'fecha_alta': (primero - timedelta(minutes=8 + i % 19)).isoformat(),
                                 'inicio': primero.isoformat(), 'mensajes': mensajes})
        auditoria.append({'clave': persona['clave'], 'dificultades': persona['dificultades'],
                          'recursos': persona['recursos'], 'voz': persona['voz'],
                          'contexto_idx': persona['contexto_idx'], 'mensajes': len(mensajes)})
    ruta = salida / 'actividad.json'
    contenido = (json.dumps(datos, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if ruta.exists() and ruta.read_bytes() != contenido:
        raise ValueError('El paquete existente difiere. Usa otra carpeta para una versión diferente.')
    guardar_privado(ruta, contenido)
    huella = hashlib.sha256(contenido).hexdigest()
    guardar_privado(salida / 'actividad.sha256', f'{huella}  actividad.json\n')
    guardar_privado(salida / 'perfiles_revision.json', json.dumps(auditoria, ensure_ascii=False, indent=2) + '\n')
    with (salida / 'accesos.csv').open('w', encoding='utf-8-sig', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=['clave', 'nombre', 'email', 'password'])
        escritor.writeheader()
        escritor.writerows({k: p[k] for k in escritor.fieldnames} for p in accesos.values())
    (salida / 'accesos.csv').chmod(0o600)
    print(json.dumps({'lote': lote, 'cuentas': len(personas),
                      'mensajes': sum(len(c['mensajes']) for c in datos['cuentas']),
                      'sha256': huella, 'salida': str(salida)}, ensure_ascii=False), flush=True)
    return datos


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fecha', default='2026-09-11', type=date.fromisoformat)
    parser.add_argument('--salida', type=Path, default=RAIZ / 'entregas_locales' / 'actividad_20260911')
    args = parser.parse_args()
    preparar(args.fecha, args.salida.resolve())


if __name__ == '__main__':
    main()
