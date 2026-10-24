"""Completa el lote con el Ollama del equipo, en una BD privada separada."""
import argparse
from pathlib import Path
import time

from cargar import Carga, bloqueo, conectar
from intercambio import escribir_comprimido, paquete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--backend', required=True)
    args = parser.parse_args()
    conectar(args.backend)
    from django.conf import settings
    from ml.ollama import ErrorModelo
    carpeta = Path(args.carpeta).resolve()
    if Path(settings.DATABASES['default']['NAME']).resolve().parent != carpeta:
        raise ValueError('Selecciona explícitamente la base aislada con DJANGO_DB_PATH.')
    carga = Carga(Path(__file__).with_name('historias.json'), carpeta, 'colegio-20261023-20')
    with bloqueo(carpeta):
        from reportes.services import actualizar_reporte
        from sesiones.models import SesionSemanal
        from chat.models import Mensaje
        from django.db.models import Q
        ids = [carga.usuario(p['clave']).pk for p in carga.personas]
        for sesion in SesionSemanal.objects.filter(usuario_id__in=ids):
            actualizar_reporte(sesion)
        errores = 0
        directo_inicial = settings.OLLAMA_CHAT_DIRECT
        while not carga.estado()['completo']:
            try:
                # Reparte el avance entre cuentas; cada alumno mantiene su orden.
                cantidades = {p['clave']: Mensaje.objects.filter(
                    usuario_id=carga.manifiesto['cuentas'][p['clave']]['id'],
                    remitente='usuario', analisis_estado='listo', respuesta__isnull=False,
                ).count() for p in carga.personas}
                pendientes = set(Mensaje.objects.filter(remitente='usuario').filter(
                    ~Q(analisis_estado='listo') | Q(respuesta__isnull=True),
                ).values_list('usuario_id', flat=True))
                carga.personas.sort(key=lambda p: (
                    carga.manifiesto['cuentas'][p['clave']]['id'] not in pendientes,
                    cantidades[p['clave']],
                ))
                carga.procesar(max_pasos=1, pausa=0)
                escribir_comprimido(carpeta / 'resultados-modelo.json.gz', paquete(carga))
                errores = 0
                settings.OLLAMA_CHAT_DIRECT = directo_inicial
            except (RuntimeError, OSError, ErrorModelo) as error:
                errores += 1
                carga.evento('reintento_local', intento=errores, clase=type(error).__name__)
                if errores >= 8:
                    raise
                if isinstance(error, ErrorModelo) and errores >= 3:
                    # Modo nativo ya soportado por la app: da margen para acabar.
                    # Solo afecta esta generación en la copia privada.
                    settings.OLLAMA_CHAT_DIRECT = False
                time.sleep(1 if isinstance(error, ErrorModelo) else 60)
            if (carpeta / 'detener').exists():
                return
        carga.exportar()
        carga.evento('completo_en_equipo', **carga.estado(escribir=True))


if __name__ == '__main__':
    main()
