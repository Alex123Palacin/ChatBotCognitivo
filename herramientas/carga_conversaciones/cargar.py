"""Carga histórica independiente. No cambia el código ni el reloj del programa.

Los personajes se documentan en historias.json; las respuestas y evidencias se
obtienen del modelo configurado. Las credenciales y el progreso son privados.
"""
import argparse
from contextlib import contextmanager, closing
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import time
import unicodedata
import uuid
from zoneinfo import ZoneInfo


def guardar(ruta, valor):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporal = ruta.with_suffix(ruta.suffix + '.tmp')
    with temporal.open('w', encoding='utf-8') as archivo:
        os.chmod(temporal, 0o600)
        json.dump(valor, archivo, ensure_ascii=False, indent=2)
    temporal.replace(ruta)


def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding='utf-8'))


def historias(ruta):
    datos = leer(ruta)
    personas = datos.get('personas', [])
    claves = set()
    for persona in personas:
        clave = persona.get('clave', '')
        if not re.fullmatch(r'p\d{2}', clave) or clave in claves:
            raise ValueError('Cada persona necesita una clave única p01, p02, ...')
        claves.add(clave)
        if not 1 <= len(persona.get('nombre', '')) <= 150 or len(persona.get('semanas', [])) != 4:
            raise ValueError('Falta nombre o alguna de las cuatro semanas.')
        for semana in persona['semanas']:
            if not 2 <= len(semana) <= 4 or any(not isinstance(m, str) or not 1 <= len(m.strip()) <= 2000 for m in semana):
                raise ValueError('Cada semana necesita entre 2 y 4 mensajes válidos.')
    if not personas:
        raise ValueError('El archivo no contiene personas.')
    huella = hashlib.sha256(json.dumps(datos, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return personas, huella


def conectar(backend):
    sys.path.insert(0, str(Path(backend).resolve()))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'principal.settings')
    import django
    django.setup()


@contextmanager
def bloqueo(carpeta):
    """El bloqueo de proceso se libera incluso si el comando termina abruptamente."""
    archivo = (carpeta / 'proceso.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            archivo.seek(0); archivo.write(b'0'); archivo.flush(); archivo.seek(0)
            msvcrt.locking(archivo.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(archivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        archivo.close()


class Carga:
    def __init__(self, ruta, carpeta, lote, inicio=None):
        from django.utils import timezone
        if not re.fullmatch(r'[a-z0-9-]{3,60}', lote):
            raise ValueError('Identificador de lote no válido.')
        self.personas, self.huella = historias(ruta)
        self.carpeta = Path(carpeta).resolve()
        self.carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.ruta = self.carpeta / 'manifiesto.json'
        self.lote = lote
        if self.ruta.exists():
            self.manifiesto = leer(self.ruta)
            if self.manifiesto['lote'] != lote or self.manifiesto['historias_sha256'] != self.huella:
                raise ValueError('La carpeta ya pertenece a otro lote o a otras historias.')
            if inicio and datetime.fromisoformat(inicio) != datetime.fromisoformat(self.manifiesto['inicio']):
                raise ValueError('No se pueden cambiar las fechas al reanudar.')
        else:
            # Se cierran las cuatro semanas antes de la fecha real de ejecución.
            fecha = datetime.fromisoformat(inicio) if inicio else (timezone.localtime(timezone.now(), ZoneInfo('America/Lima')) - timedelta(days=29)).replace(hour=9, minute=0, second=0, microsecond=0)
            if fecha.tzinfo is None or fecha + timedelta(days=28, hours=5) >= timezone.now():
                raise ValueError('El inicio debe incluir zona horaria y dejar cerradas las cuatro semanas.')
            self.manifiesto = {'version': 1, 'lote': lote, 'origen': 'Personajes ficticios; no son participantes de investigación.', 'historias_sha256': self.huella, 'inicio': fecha.isoformat(), 'cuentas': {}, 'eliminado': False}
            self.persistir()
        if self.manifiesto.get('eliminado'):
            raise ValueError('Este lote ya fue eliminado. Usa otro lote para una nueva carga.')
        self.inicio = datetime.fromisoformat(self.manifiesto['inicio'])

    def persistir(self):
        guardar(self.ruta, self.manifiesto)

    def evento(self, tipo, **datos):
        from django.utils import timezone
        print(json.dumps({'fecha': timezone.now().isoformat(), 'evento': tipo, **datos}, ensure_ascii=False), flush=True)

    def preparar(self):
        from django.contrib.auth.hashers import make_password
        for indice, persona in enumerate(self.personas):
            clave = persona['clave']
            if clave not in self.manifiesto['cuentas']:
                nombre = unicodedata.normalize('NFKD', persona['nombre']).encode('ascii', 'ignore').decode().lower().split()
                sufijo = hashlib.sha256((self.lote + self.huella + clave).encode()).hexdigest()[:12]
                password = secrets.token_urlsafe(18)
                self.manifiesto['cuentas'][clave] = {'id': None, 'nombre': persona['nombre'], 'email': f'{nombre[0]}.{nombre[1]}.{sufijo}@gmail.com', 'password': password, 'password_hash': make_password(password), 'inicio': (self.inicio + timedelta(minutes=indice * 12)).isoformat()}
        # Se escribe antes de crear: permite recuperar una interrupción tras COMMIT.
        self.persistir()

    def usuario(self, clave, permitir_ausente=False):
        from django.contrib.auth import get_user_model
        registro = self.manifiesto['cuentas'][clave]
        qs = get_user_model().objects
        usuario = qs.filter(pk=registro['id']).first() if registro['id'] else qs.filter(username=registro['email']).first()
        if usuario is None and permitir_ausente:
            return None
        if usuario is None or usuario.username != registro['email'] or usuario.email != registro['email'] or usuario.first_name != registro['nombre'] or usuario.password != registro['password_hash'] or usuario.is_staff or usuario.is_superuser:
            raise ValueError(f'La identidad de {clave} no coincide con el manifiesto. No se modificó esa cuenta.')
        return usuario

    def respaldo(self):
        from django.conf import settings
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise ValueError('Este respaldo está preparado para la base SQLite del proyecto.')
        ruta = self.carpeta / 'respaldo-anterior.sqlite3'
        if not ruta.exists():
            with sqlite3.connect(str(settings.DATABASES['default']['NAME'])) as origen, sqlite3.connect(str(ruta)) as destino:
                origen.backup(destino)
            os.chmod(ruta, 0o600)

    def cargar(self, respaldo=True):
        from django.contrib.auth import get_user_model
        from django.db import transaction
        from sesiones.services import iniciar_programa, actualizar_semanas
        from usuarios.models import Perfil
        self.preparar()
        # Detectar colisiones en todo el lote antes de crear la primera cuenta.
        for persona in self.personas:
            self.usuario(persona['clave'], permitir_ausente=True)
        if respaldo:
            self.respaldo()
        for persona in self.personas:
            clave = persona['clave']; registro = self.manifiesto['cuentas'][clave]
            with transaction.atomic():
                usuario = self.usuario(clave, permitir_ausente=True)
                if usuario is None:
                    usuario = get_user_model().objects.create(username=registro['email'], email=registro['email'], first_name=registro['nombre'], password=registro['password_hash'], is_active=True, is_staff=False, is_superuser=False, date_joined=datetime.fromisoformat(registro['inicio']) - timedelta(days=1))
                perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
                if hasattr(perfil, 'origen_datos'):
                    perfil.origen_datos = 'demostracion'
                    perfil.save(update_fields=['origen_datos'])
                iniciar_programa(perfil, datetime.fromisoformat(registro['inicio']))
                actualizar_semanas(usuario)
            registro['id'] = usuario.pk
            self.persistir()
        self.evento('cuentas_preparadas', cantidad=len(self.personas), sesiones=len(self.personas) * 4)

    def id_mensaje(self, clave, semana, turno, rol='usuario'):
        return uuid.uuid5(uuid.NAMESPACE_URL, f'chatcognitivo/{self.lote}/{self.huella}/{clave}/{semana}/{turno}/{rol}')

    def fecha_visita(self, sesion, turno, total):
        if self.manifiesto.get('calendario', {}).get('visitas') == 'inicio-fin':
            primero = sesion.inicio + timedelta(days=1 if sesion.numero > 1 else 0)
            ultimo = sesion.fin - timedelta(minutes=30)
            return primero + (ultimo - primero) * turno / (total - 1)
        return sesion.inicio + timedelta(days=turno * 2, minutes=turno * 17)

    def mensaje(self, persona, semana, turno, texto):
        from chat.models import Mensaje
        from django.db import transaction
        from sesiones.models import SesionSemanal
        clave = persona['clave']; usuario = self.usuario(clave)
        sesion = SesionSemanal.objects.get(usuario=usuario, numero=semana)
        # Cada sesión tiene visitas separadas por días, sin mover el reloj global.
        fecha = self.fecha_visita(sesion, turno, len(persona['semanas'][semana - 1]))
        identificador = self.id_mensaje(clave, semana, turno)
        with transaction.atomic():
            m, _ = Mensaje.objects.get_or_create(pk=identificador, defaults={'usuario': usuario, 'sesion': sesion, 'contenido': texto, 'remitente': 'usuario', 'fecha': fecha, 'clave_envio': identificador})
            if m.usuario_id != usuario.pk or m.sesion_id != sesion.pk or m.contenido != texto or m.fecha != fecha or m.remitente != 'usuario' or m.clave_envio != identificador:
                raise ValueError('Un mensaje existente no coincide con la historia. Carga detenida.')
        return m

    def responder(self, mensaje):
        from chat.models import Mensaje
        from chat.services import historial_modelo, contexto_modelo
        from django.db.models import Q
        from django.utils import timezone
        from ml.conversacion import responder_conversacion_stream
        from usuarios.models import Perfil
        if Mensaje.objects.filter(respuesta_a=mensaje).exists():
            return
        # Esperar a los chats reales entre operaciones. Nunca se detiene el worker.
        self.esperar_chat()
        token = str(uuid.uuid4())
        propio = Perfil.objects.filter(usuario=mensaje.usuario).filter(Q(respuesta_hasta__isnull=True) | Q(respuesta_hasta__lte=timezone.now()))
        if not propio.update(respuesta_hasta=timezone.now() + timedelta(seconds=240), respuesta_token=token):
            raise RuntimeError('Esta cuenta tiene una respuesta activa. Reintenta más tarde.')
        try:
            historial = historial_modelo(mensaje.usuario, hasta=mensaje)
            historial.append({'role': 'user', 'content': mensaje.contenido})
            with closing(responder_conversacion_stream(historial, contexto_modelo(mensaje.usuario, mensaje.sesion))) as flujo:
                texto = ''.join(flujo).strip()
            if not texto:
                raise ValueError('Ollama devolvió una respuesta vacía.')
            if not Perfil.objects.filter(usuario=mensaje.usuario, respuesta_token=token).exists():
                raise RuntimeError('La reserva de respuesta cambió. No se guardó una respuesta ajena.')
            Mensaje.objects.get_or_create(respuesta_a=mensaje, defaults={'id': uuid.uuid5(mensaje.id, 'asistente'), 'usuario': mensaje.usuario, 'sesion': mensaje.sesion, 'remitente': 'asistente', 'contenido': texto, 'fecha': mensaje.fecha + timedelta(seconds=20), 'analisis_estado': 'listo'})
            Perfil.objects.filter(usuario=mensaje.usuario).update(ultima_actividad=mensaje.fecha + timedelta(seconds=20), conectado=False)
        finally:
            Perfil.objects.filter(usuario=mensaje.usuario, respuesta_token=token).update(respuesta_hasta=None, respuesta_token='')

    def esperar_chat(self):
        from reportes.services import hay_respuesta_activa
        while hay_respuesta_activa():
            if (self.carpeta / 'detener').exists():
                raise InterruptedError('Se pidió detener la carga.')
            time.sleep(3)

    def procesar(self, max_pasos=0, pausa=1):
        from django.db import close_old_connections
        from django.utils import timezone
        from reportes.services import analizar_pendiente, actualizar_reporte
        pasos = 0
        for persona in self.personas:
            for numero, textos in enumerate(persona['semanas'], 1):
                for turno, texto in enumerate(textos):
                    if (self.carpeta / 'detener').exists():
                        self.evento('detenido'); return
                    close_old_connections()
                    m = self.mensaje(persona, numero, turno, texto)
                    completo = hasattr(m, 'respuesta') and m.analisis_estado == 'listo'
                    if completo:
                        continue
                    self.evento('generando', persona=persona['clave'], semana=numero, turno=turno + 1)
                    self.responder(m)
                    self.evento('respuesta_guardada', persona=persona['clave'], semana=numero, turno=turno + 1)
                    # Usa reservas y validación de citas del procesador real.
                    intentos = 0
                    while m.analisis_estado != 'listo':
                        if (self.carpeta / 'detener').exists():
                            self.evento('detenido'); return
                        self.esperar_chat()
                        m.refresh_from_db()
                        if m.analisis_estado == 'listo':
                            break
                        if m.analisis_hasta and m.analisis_hasta > timezone.now():
                            time.sleep(3); continue
                        if analizar_pendiente(m):
                            m.refresh_from_db(); break
                        m.refresh_from_db()
                        if m.analisis_estado == 'error':
                            intentos += 1
                            if intentos >= 3:
                                raise RuntimeError(f'El análisis de {persona["clave"]}, semana {numero}, no se completó. Puede reanudarse.')
                    actualizar_reporte(m.sesion)
                    pasos += 1
                    estado = self.estado(escribir=True)
                    self.evento('avance', persona=persona['clave'], semana=numero, turno=turno + 1, respondidos=estado['respuestas'], analizados=estado['analizados'], reportes_listos=estado['reportes_listos'])
                    if max_pasos and pasos >= max_pasos:
                        return
                    time.sleep(max(0, pausa))
        estado = self.estado(escribir=True)
        self.evento('finalizado' if estado['completo'] else 'incompleto', **estado)

    def estado(self, escribir=False):
        from chat.models import Mensaje
        from reportes.models import Evidencia, ReporteSemanal
        from sesiones.models import SesionSemanal
        ids = [self.usuario(p['clave']).pk for p in self.personas]
        mensajes = Mensaje.objects.filter(usuario_id__in=ids, remitente='usuario')
        previstos = sum(len(s) for p in self.personas for s in p['semanas'])
        r = {'cuentas': len(ids), 'sesiones': SesionSemanal.objects.filter(usuario_id__in=ids).count(), 'mensajes_previstos': previstos, 'mensajes_estudiante': mensajes.count(), 'respuestas': mensajes.filter(respuesta__isnull=False).count(), 'analizados': mensajes.filter(analisis_estado='listo').count(), 'reportes': ReporteSemanal.objects.filter(sesion__usuario_id__in=ids).count(), 'reportes_listos': ReporteSemanal.objects.filter(sesion__usuario_id__in=ids, estado='listo', mensajes_estudiante__gt=0).count(), 'citas_invalidas': sum(e.cita not in e.mensaje.contenido for e in Evidencia.objects.filter(mensaje__usuario_id__in=ids).select_related('mensaje'))}
        esperados = {(self.manifiesto['cuentas'][p['clave']]['id'], n): len(s) for p in self.personas for n, s in enumerate(p['semanas'], 1)}
        r['reportes_listos'] = sum(reporte.mensajes_estudiante == esperados[(reporte.sesion.usuario_id, reporte.sesion.numero)] for reporte in ReporteSemanal.objects.filter(sesion__usuario_id__in=ids, estado='listo').select_related('sesion'))
        r['completo'] = r['sesiones'] == len(ids) * 4 and r['mensajes_estudiante'] == previstos and r['respuestas'] == previstos and r['analizados'] == previstos and r['reportes_listos'] == len(ids) * 4 and r['citas_invalidas'] == 0
        if escribir:
            guardar(self.carpeta / 'estado.json', r)
        return r

    def exportar(self):
        from chat.models import Mensaje
        from reportes.services import reporte_actual_json
        salida = []
        credenciales = []
        for persona in self.personas:
            usuario = self.usuario(persona['clave'])
            r = self.manifiesto['cuentas'][persona['clave']]
            credenciales.append({'nombre': r['nombre'], 'usuario': r['email'], 'password': r['password']})
            salida.append({'usuario_id': usuario.pk, 'nombre': usuario.first_name, 'sesiones': [reporte_actual_json(s) for s in usuario.semanas.all()], 'mensajes': [{'id': str(m.pk), 'semana': m.sesion.numero, 'remitente': m.remitente, 'fecha': m.fecha.isoformat(), 'contenido': m.contenido} for m in Mensaje.objects.filter(usuario=usuario).select_related('sesion').order_by('fecha')]})
        guardar(self.carpeta / 'credenciales.json', credenciales)
        guardar(self.carpeta / 'resultados.json', {'origen': self.manifiesto['origen'], 'lote': self.lote, 'estado': self.estado(), 'personas': salida})

    def limpiar(self, confirmar=None):
        from django.db import transaction
        with transaction.atomic():
            usuarios = [self.usuario(p['clave']) for p in self.personas]
            ids = [u.pk for u in usuarios]
            self.evento('cuentas_para_eliminar', ids=ids, cantidad=len(ids))
            if confirmar != self.lote:
                return
            # Se valida toda la identidad antes de la primera eliminación.
            for u in usuarios:
                u.delete()
        self.manifiesto['eliminado'] = True
        self.persistir()
        self.evento('lote_eliminado', cantidad=len(ids))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=['plan', 'cargar', 'procesar', 'estado', 'exportar', 'limpiar'])
    parser.add_argument('--historias', default=str(Path(__file__).with_name('historias.json')))
    defecto = '/app' if Path('/app/manage.py').exists() else str(Path(__file__).resolve().parents[2] / 'backend' / 'principal')
    parser.add_argument('--backend', default=defecto)
    parser.add_argument('--carpeta', required=True, help='Carpeta privada y persistente, fuera de Git y del directorio público.')
    parser.add_argument('--lote', default='colegio-20261023-20')
    parser.add_argument('--inicio', help='Fecha histórica ISO con zona horaria. Se fija en la primera ejecución.')
    parser.add_argument('--max-pasos', type=int, default=0)
    parser.add_argument('--confirmar-lote')
    args = parser.parse_args()
    personas, _ = historias(args.historias)
    if args.accion == 'plan':
        print(json.dumps({'cuentas': len(personas), 'sesiones': len(personas) * 4, 'mensajes_estudiante': sum(len(s) for p in personas for s in p['semanas']), 'nombres': [p['nombre'] for p in personas]}, ensure_ascii=False, indent=2))
        return
    conectar(args.backend)
    carga = Carga(args.historias, args.carpeta, args.lote, args.inicio)
    if args.accion == 'estado':
        print(json.dumps(carga.estado(), ensure_ascii=False, indent=2)); return
    with bloqueo(carga.carpeta):
        if args.accion == 'cargar': carga.cargar()
        elif args.accion == 'procesar': carga.procesar(args.max_pasos); carga.exportar()
        elif args.accion == 'exportar': carga.exportar()
        elif args.accion == 'limpiar': carga.limpiar(args.confirmar_lote)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, InterruptedError, OSError) as exc:
        print(f'Carga detenida: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
