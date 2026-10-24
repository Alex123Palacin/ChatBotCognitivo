"""Añade cuatro intercambios por semana al lote ficticio, sin sobrescribir mensajes.

El modo generar solo admite la base privada separada. El modo incorporar valida
propietarios, contenido, calendario, citas y respuestas antes de una transacción.
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import time
import uuid

if __package__:
    from .cargar import Carga, bloqueo, conectar, guardar, leer
    from .intercambio import escribir_comprimido, leer_comprimido
else:
    from cargar import Carga, bloqueo, conectar, guardar, leer
    from intercambio import escribir_comprimido, leer_comprimido


class Ampliacion:
    def __init__(self, carga, ruta):
        self.carga = carga
        self.datos = leer(ruta)
        self.sha = hashlib.sha256(json.dumps(self.datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.previstos = {}
        self.usuarios = {}
        self.sesiones = {}
        from sesiones.models import SesionSemanal
        claves = set()
        for persona in self.datos['personas']:
            clave = persona['clave']
            if clave in claves or clave not in carga.manifiesto['cuentas'] or len(persona['semanas']) != 4:
                raise ValueError('Persona repetida, ajena o sin cuatro semanas.')
            claves.add(clave)
            usuario = carga.usuario(clave)
            self.usuarios[usuario.pk] = usuario
            for numero, textos in enumerate(persona['semanas'], 1):
                sesion = SesionSemanal.objects.get(usuario=usuario, numero=numero)
                self.sesiones[sesion.pk] = sesion
                if len(textos) != 4:
                    raise ValueError('Se requieren cuatro mensajes nuevos por semana.')
                primero = carga.fecha_visita(sesion, 0, 2)
                ultimo = carga.fecha_visita(sesion, 1, 2)
                for turno, texto in enumerate(textos, 1):
                    if not isinstance(texto, str) or not 1 <= len(texto.strip()) <= 2000:
                        raise ValueError('Mensaje no válido.')
                    mid = uuid.uuid5(uuid.NAMESPACE_URL, f'chatcognitivo/ampliacion/{carga.lote}/{self.sha}/{clave}/{numero}/{turno}')
                    fecha = primero + (ultimo - primero) * turno / 5
                    self.previstos[mid] = dict(usuario_id=usuario.pk, sesion_id=sesion.pk, contenido=texto, fecha=fecha, remitente='usuario', clave_envio=mid, respuesta_a_id=None)
                    self.previstos[uuid.uuid5(mid, 'asistente')] = dict(usuario_id=usuario.pk, sesion_id=sesion.pk, contenido=None, fecha=fecha + timedelta(seconds=20), remitente='asistente', clave_envio=None, respuesta_a_id=mid)
        if claves != {p['clave'] for p in carga.personas}:
            raise ValueError('La ampliación debe corresponder al mismo conjunto de personajes.')

    def estado(self):
        from chat.models import Mensaje
        qs = Mensaje.objects.filter(pk__in=self.previstos)
        return dict(mensajes=qs.count(), esperados=len(self.previstos), analizados=qs.filter(remitente='usuario', analisis_estado='listo').count(), respuestas=qs.filter(remitente='asistente').count())

    def generar(self, destino):
        from django.conf import settings
        from chat.models import Mensaje
        from chat.services import historial_modelo
        from ml.conversacion import responder_conversacion
        from ml.analisis import analizar_mensaje, INDICADORES, SENALES_INDICADOR
        from reportes.models import Evidencia
        from reportes.services import actualizar_reporte
        from django.db import transaction
        if Path(settings.DATABASES['default']['NAME']).resolve().parent != self.carga.carpeta or not (self.carga.carpeta / 'aislada.sqlite3').exists():
            raise ValueError('Solo se genera en la base aislada seleccionada explícitamente.')
        if set(Mensaje.objects.values_list('usuario_id', flat=True)) - set(self.usuarios):
            raise ValueError('La base aislada contiene conversaciones ajenas al lote.')
        for mid, datos in self.previstos.items():
            if datos['remitente'] != 'usuario':
                continue
            if (self.carga.carpeta / 'detener-ampliacion').exists():
                return
            defaults = {k: v for k, v in datos.items() if k != 'contenido'}
            mensaje, _ = Mensaje.objects.get_or_create(pk=mid, defaults={**defaults, 'contenido': datos['contenido']})
            self.validar_mensaje(mensaje, datos)
            usuario = self.usuarios[mensaje.usuario_id]
            historial = historial_modelo(usuario, hasta=mensaje)
            rid = uuid.uuid5(mid, 'asistente')
            if not Mensaje.objects.filter(pk=rid).exists():
                contexto = {'nombre': usuario.first_name, 'semana': self.sesiones[mensaje.sesion_id].numero, 'resumen': ' / '.join(h['content'] for h in historial[-6:] if h['role'] == 'user')[:600]}
                for intento in range(5):
                    try:
                        respuesta = responder_conversacion([*historial, {'role': 'user', 'content': mensaje.contenido}], contexto)
                        if not respuesta.strip():
                            raise RuntimeError('Respuesta vacía.')
                        break
                    except Exception:
                        if intento == 4:
                            raise
                        time.sleep(1)
                Mensaje.objects.create(pk=rid, **{**self.previstos[rid], 'contenido': respuesta, 'analisis_estado': 'listo'})
            if mensaje.analisis_estado != 'listo':
                resultados = analizar_mensaje(mensaje.contenido, historial[-10:])
                citas = []
                for e in resultados:
                    if e.get('indicador') not in INDICADORES or e.get('senal') not in SENALES_INDICADOR[e['indicador']] or not isinstance(e.get('cita'), str) or not e['cita'].strip() or e['cita'] not in mensaje.contenido or not e.get('observacion', '').strip():
                        raise ValueError('El modelo devolvió una cita no verificable.')
                    citas.append(Evidencia(mensaje=mensaje, **e))
                with transaction.atomic():
                    Evidencia.objects.bulk_create(citas, ignore_conflicts=True)
                    Mensaje.objects.filter(pk=mid).update(analisis_estado='listo', analisis_hasta=None)
            actualizar_reporte(self.sesiones[mensaje.sesion_id])
            estado = self.estado()
            guardar(self.carga.carpeta / 'ampliacion-estado.json', estado)
            print(json.dumps(estado), flush=True)
        from django.core import serializers
        objetos = [*Mensaje.objects.filter(pk__in=self.previstos), *Evidencia.objects.filter(mensaje_id__in=self.previstos)]
        escribir_comprimido(destino, {'lote': self.carga.lote, 'origen': self.datos['origen'], 'ampliacion_sha256': self.sha, 'objetos': json.loads(serializers.serialize('json', objetos))})

    @staticmethod
    def validar_mensaje(mensaje, previsto):
        for campo, valor in previsto.items():
            if valor is not None and getattr(mensaje, campo) != valor:
                raise ValueError(f'Un mensaje existente difiere en {campo}. No se sobrescribe.')
        if not mensaje.contenido.strip():
            raise ValueError('Contenido vacío.')

    def incorporar(self, paquete):
        from django.db import transaction
        from chat.models import Mensaje
        from reportes.models import Evidencia
        from reportes.services import actualizar_reporte
        from usuarios.models import Perfil
        from ml.analisis import INDICADORES, SENALES_INDICADOR
        if paquete.get('lote') != self.carga.lote or paquete.get('ampliacion_sha256') != self.sha or paquete.get('origen') != self.datos['origen']:
            raise ValueError('El paquete pertenece a otra ampliación.')
        mensajes, evidencias = {}, []
        for objeto in paquete['objetos']:
            if objeto['model'] == 'chat.mensaje':
                mid = uuid.UUID(objeto['pk'])
                if mid not in self.previstos or mid in mensajes:
                    raise ValueError('Mensaje ajeno o duplicado.')
                f = objeto['fields']
                m = Mensaje(id=mid, usuario_id=f['usuario'], sesion_id=f['sesion'], contenido=f['contenido'], fecha=datetime.fromisoformat(f['fecha']), remitente=f['remitente'], clave_envio=uuid.UUID(f['clave_envio']) if f['clave_envio'] else None, respuesta_a_id=uuid.UUID(f['respuesta_a']) if f['respuesta_a'] else None, analisis_estado=f['analisis_estado'])
                self.validar_mensaje(m, self.previstos[mid])
                if m.analisis_estado != 'listo' or (m.remitente == 'usuario' and m.respuesta_a_id is not None) or (m.remitente == 'asistente' and m.clave_envio is not None):
                    raise ValueError('Mensaje incompleto o asociación inválida.')
                mensajes[mid] = m
            elif objeto['model'] == 'reportes.evidencia':
                evidencias.append(objeto['fields'])
            else:
                raise ValueError('No se importan cuentas, contraseñas ni otros modelos.')
        if set(mensajes) != set(self.previstos):
            raise ValueError('Faltan mensajes para completar la ampliación.')
        vistas = set()
        for e in evidencias:
            m = mensajes.get(uuid.UUID(e['mensaje']))
            clave = (e['mensaje'], e['indicador'], e['cita'])
            if not m or m.remitente != 'usuario' or e['indicador'] not in INDICADORES or e['senal'] not in SENALES_INDICADOR[e['indicador']] or not e['cita'].strip() or e['cita'] not in m.contenido or not e['observacion'].strip() or clave in vistas:
                raise ValueError('Evidencia ajena, duplicada o no literal.')
            vistas.add(clave)
        self.carga.respaldo()
        with transaction.atomic():
            # Revalida identidades dentro de la transacción antes de escribir.
            for p in self.carga.personas:
                self.carga.usuario(p['clave'])
            for mid in mensajes:
                anterior = Mensaje.objects.filter(pk=mid).first()
                if anterior:
                    self.validar_mensaje(anterior, {**self.previstos[mid], 'contenido': mensajes[mid].contenido})
                    esperadas = {(e['indicador'], e['cita'], e['senal'], e['observacion']) for e in evidencias if e['mensaje'] == str(mid)}
                    if set(anterior.evidencias.values_list('indicador', 'cita', 'senal', 'observacion')) != esperadas:
                        raise ValueError('No se reemplaza un análisis ya guardado.')
            for rol in ('usuario', 'asistente'):
                for mid, m in mensajes.items():
                    if m.remitente == rol and not Mensaje.objects.filter(pk=mid).exists():
                        m.save(force_insert=True)
            for e in evidencias:
                Evidencia.objects.get_or_create(mensaje_id=e['mensaje'], indicador=e['indicador'], cita=e['cita'], defaults={'senal': e['senal'], 'observacion': e['observacion']})
            Perfil.objects.filter(usuario_id__in=self.usuarios).update(origen_datos='demostracion')
            for uid in self.usuarios:
                Perfil.objects.filter(usuario_id=uid).update(ultima_actividad=Mensaje.objects.filter(usuario_id=uid, remitente='usuario').order_by('-fecha').values_list('fecha', flat=True).first())
            for sesion in self.sesiones.values():
                actualizar_reporte(sesion)
        return self.estado()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=['generar', 'incorporar'])
    parser.add_argument('--backend', required=True)
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--paquete', required=True)
    args = parser.parse_args()
    conectar(args.backend)
    carga = Carga(Path(__file__).with_name('historias.json'), args.carpeta, 'colegio-20261023-20')
    ampliacion = Ampliacion(carga, Path(__file__).with_name('ampliacion.json'))
    with bloqueo(carga.carpeta):
        if args.accion == 'generar':
            ampliacion.generar(args.paquete)
        else:
            print(json.dumps(ampliacion.incorporar(leer_comprimido(args.paquete))))


if __name__ == '__main__':
    main()
