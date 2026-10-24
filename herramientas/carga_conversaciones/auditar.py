"""Comprueba el lote terminado y conserva un resumen sin contraseñas."""
import argparse
from datetime import timedelta
from pathlib import Path
import sqlite3

if __package__:
    from .cargar import Carga, conectar, guardar
else:
    from cargar import Carga, conectar, guardar


def auditar(carga):
    from django.contrib.auth import authenticate, get_user_model
    from django.utils import timezone
    from chat.models import Mensaje
    from reportes.models import Evidencia
    estado = carga.estado()
    if not estado['completo']:
        raise ValueError('El lote aún no está completo.')
    personas = []
    for p in carga.personas:
        usuario = carga.usuario(p['clave'])
        registro = carga.manifiesto['cuentas'][p['clave']]
        if authenticate(username=usuario.username, password=registro['password']) is None:
            raise ValueError('Una credencial del lote no autentica correctamente.')
        semanas = list(usuario.semanas.all().select_related('reporte'))
        mensajes = list(Mensaje.objects.filter(usuario=usuario).order_by('fecha'))
        for s in semanas:
            if s.fin - s.inicio != timedelta(days=7) or s.estado != 'cerrada':
                raise ValueError('Una sesión no tiene el calendario esperado.')
            if s.mensajes.filter(fecha__lt=s.inicio).exists() or s.mensajes.filter(fecha__gte=s.fin).exists():
                raise ValueError('Hay un mensaje fuera de su sesión.')
            if s.reporte.total_evidencias != Evidencia.objects.filter(mensaje__sesion=s).count():
                raise ValueError('Un reporte tiene un contador de evidencias incorrecto.')
        if usuario.perfil.ultima_actividad != mensajes[-1].fecha:
            raise ValueError('La fecha de actividad no coincide con el último mensaje.')
        personas.append({'id': usuario.pk, 'nombre': usuario.first_name,
                         'primer_mensaje': mensajes[0].fecha.isoformat(),
                         'ultimo_mensaje': mensajes[-1].fecha.isoformat(),
                         'mensajes_estudiante': sum(m.remitente == 'usuario' for m in mensajes),
                         'respuestas': sum(m.remitente == 'asistente' for m in mensajes),
                         'reportes': [{'id': s.reporte.pk, 'semana': s.numero, 'estado': s.reporte.estado,
                                      'mensajes': s.reporte.mensajes_estudiante,
                                      'evidencias': s.reporte.total_evidencias} for s in semanas]})
    copia = carga.carpeta / 'respaldo-anterior.sqlite3'
    con = sqlite3.connect(str(copia))
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('No se pudo comprobar el respaldo anterior.')
        campos = ['id', 'username', 'email', 'password', 'is_staff', 'is_superuser']
        anteriores = con.execute('SELECT ' + ','.join(campos) + ' FROM auth_user ORDER BY id').fetchall()
    finally:
        con.close()
    actuales = list(get_user_model().objects.filter(pk__in=[r[0] for r in anteriores]).order_by('id').values_list(*campos))
    if anteriores != actuales:
        raise ValueError('Revisar las identidades o credenciales de cuentas previas.')
    resultado = {'fecha_real_verificacion': timezone.now().isoformat(),
                 'origen': carga.manifiesto['origen'], 'estado': estado,
                 'cuentas_previas_conservadas': len(anteriores), 'credenciales_verificadas': len(personas),
                 'personas': personas}
    guardar(carga.carpeta / 'auditoria-final.json', resultado)
    return {k: v for k, v in resultado.items() if k != 'personas'}


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--backend', default='/app')
    args = parser.parse_args()
    conectar(args.backend)
    carga = Carga(Path(__file__).with_name('historias.json'), args.carpeta, 'colegio-20261023-20')
    print(json.dumps(auditar(carga), ensure_ascii=False))


if __name__ == '__main__':
    main()
