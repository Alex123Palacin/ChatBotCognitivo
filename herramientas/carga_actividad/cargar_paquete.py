"""Entrada portable: usa las dependencias y la configuración del backend existente."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--backend', type=Path, default=Path('/app'))
    parser.add_argument('--aplicar', action='store_true')
    parser.add_argument('--respaldo', type=Path)
    args = parser.parse_args()
    backend = args.backend.resolve()
    if not (backend / 'manage.py').is_file() or not (backend / 'principal' / 'settings.py').is_file():
        parser.error('La ruta --backend debe contener manage.py y principal/settings.py.')
    sys.path.insert(0, str(backend))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'principal.settings')
    import django
    django.setup()
    from django.db import DatabaseError
    # En el paquete el motor está junto a esta entrada; no requiere instalar
    # herramientas en el contenedor ni alterar archivos de la aplicación.
    from motor_carga import ErrorCarga, importar_paquete, leer_paquete
    try:
        datos = leer_paquete(args.archivo, args.sha256)
        resultado = importar_paquete(datos, aplicar=args.aplicar, respaldo=args.respaldo)
    except (ErrorCarga, OSError, DatabaseError) as exc:
        mensaje = str(exc) if isinstance(exc, ErrorCarga) else 'No se completó la operación. Revisa la configuración de la base, rutas y permisos.'
        parser.exit(1, f'Error: {mensaje}\n')
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == '__main__':
    main()
