"""Auditoría del paquete completo, sin conexión a bases de datos."""
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[2]


def verificar(salida):
    salida = Path(salida)
    contenido = (salida / 'actividad.json').read_bytes()
    huella = hashlib.sha256(contenido).hexdigest()
    assert (salida / 'actividad.sha256').read_text().split()[0] == huella, 'Huella incorrecta'
    datos = json.loads(contenido)
    perfiles = {p['clave']: p for p in json.loads((salida / 'perfiles_revision.json').read_text(encoding='utf-8'))}
    assert len(datos['cuentas']) == len(perfiles) == 136, 'Cantidad de cuentas incorrecta'
    minimo = datetime.fromisoformat(datos['ventana_inicio'])
    maximo = datetime.fromisoformat(datos['ventana_fin'])
    assert maximo - minimo == timedelta(hours=5)
    dificultades = Counter()
    indicadores = Counter()
    textos_por_rol = {'usuario': Counter(), 'asistente': Counter()}
    mensajes_por_cuenta = []
    ids, nombres, emails, dialogos = set(), set(), set(), set()
    citas = 0
    for cuenta in datos['cuentas']:
        perfil = perfiles[cuenta['clave']]
        mensajes = cuenta['mensajes']
        assert cuenta['nombre'] not in nombres and cuenta['email'] not in emails
        nombres.add(cuenta['nombre']); emails.add(cuenta['email'])
        assert cuenta['email'].endswith('@example.com')
        assert cuenta['password_hash'].startswith('pbkdf2_sha256$')
        assert 'password' not in cuenta and 40 <= len(mensajes) <= 60
        assert datetime.fromisoformat(cuenta['fecha_alta']) <= datetime.fromisoformat(cuenta['inicio'])
        assert cuenta['inicio'] == mensajes[0]['fecha']
        horas = set()
        encontradas = Counter()
        recursos = set()
        anterior = None
        for indice, mensaje in enumerate(mensajes):
            assert mensaje['id'] not in ids
            ids.add(mensaje['id'])
            fecha = datetime.fromisoformat(mensaje['fecha'])
            assert minimo <= fecha < maximo and (anterior is None or fecha > anterior)
            anterior = fecha
            horas.add(fecha.hour)
            rol = 'usuario' if indice % 2 == 0 else 'asistente'
            assert mensaje['remitente'] == rol and mensaje['contenido'].strip()
            assert len(mensaje['contenido']) <= 2000
            textos_por_rol[rol][mensaje['contenido']] += 1
            assert mensaje['respuesta_a'] == (mensajes[indice-1]['id'] if indice % 2 else None)
            if rol == 'asistente':
                assert not mensaje['evidencias']
            for ev in mensaje['evidencias']:
                assert rol == 'usuario' and ev['cita'] in mensaje['contenido'] and len(ev['cita']) <= 400
                assert ev['observacion'].strip()
                if ev['senal'] == 'dificultad' and ev['indicador'] in (
                    'sobrecarga_academica', 'presion_tiempo', 'sintomas_fisicos', 'sintomas_psicologicos'
                ):
                    encontradas[ev['indicador']] += 1
                if ev['senal'] == 'recurso':
                    recursos.add(ev['indicador'])
                indicadores[ev['indicador']] += 1
                citas += 1
        assert horas == {13, 14, 15, 16, 17}, f'Falta actividad horaria en {cuenta["clave"]}'
        assert set(encontradas) == set(perfil['dificultades']), f'Perfil y citas no coinciden en {cuenta["clave"]}: {dict(encontradas)}'
        assert all(n >= 2 for n in encontradas.values()), f'Evidencia demasiado aislada: {cuenta["clave"]}'
        assert recursos == set(perfil['recursos']), f'Recursos no coinciden en {cuenta["clave"]}: {recursos}'
        dificultades[len(encontradas)] += 1
        firma = hashlib.sha256('\n'.join(m['contenido'] for m in mensajes).encode()).hexdigest()
        assert firma not in dialogos, 'Conversación completa repetida'
        dialogos.add(firma)
        mensajes_por_cuenta.append(len(mensajes))
    assert dict(sorted(dificultades.items())) == {0: 4, 1: 32, 2: 36, 3: 36, 4: 28}
    resumen = {'lote': datos['lote'], 'sha256': huella, 'cuentas': 136,
               'conversaciones': len(dialogos), 'mensajes': sum(mensajes_por_cuenta),
               'mensajes_minimos': min(mensajes_por_cuenta), 'mensajes_maximos': max(mensajes_por_cuenta),
               'evidencias': citas, 'distribucion_dificultades': dict(sorted(dificultades.items())),
               'evidencias_por_indicador': dict(indicadores), 'horas': [13, 14, 15, 16, 17],
               'fecha_primera': min(m['fecha'] for c in datos['cuentas'] for m in c['mensajes']),
               'fecha_ultima': max(m['fecha'] for c in datos['cuentas'] for m in c['mensajes']),
               'textos_distintos': {r: len(c) for r, c in textos_por_rol.items()},
               'repeticiones_maximas': {r: c.most_common(1)[0][1] for r, c in textos_por_rol.items()}}
    (salida / 'verificacion_paquete.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return resumen


if __name__ == '__main__':
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'entregas_locales' / 'actividad_20260911'
    print(json.dumps(verificar(salida), ensure_ascii=False, indent=2))
