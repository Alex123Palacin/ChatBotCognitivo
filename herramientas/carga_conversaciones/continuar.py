"""Mantiene una única carga reanudable; no instala servicios ni tareas periódicas."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

if __package__:
    from .cargar import bloqueo, guardar
else:
    from cargar import bloqueo, guardar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--intentos', type=int, default=10)
    args = parser.parse_args()
    carpeta = Path(args.carpeta).resolve()
    carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
    control = carpeta / 'supervision'
    control.mkdir(mode=0o700, exist_ok=True)
    with bloqueo(control):
        for intento in range(1, args.intentos + 1):
            if (carpeta / 'detener').exists():
                guardar(control / 'estado.json', {'estado': 'detenido'}); return
            guardar(control / 'estado.json', {'estado': 'procesando', 'intento': intento, 'fecha': datetime.now(timezone.utc).isoformat()})
            proceso = subprocess.run([sys.executable, str(Path(__file__).with_name('cargar.py')), 'procesar', '--carpeta', str(carpeta)], check=False)
            estado = json.loads((carpeta / 'estado.json').read_text()) if (carpeta / 'estado.json').exists() else {}
            if proceso.returncode == 0 and estado.get('completo'):
                guardar(control / 'estado.json', {'estado': 'completo', 'fecha': datetime.now(timezone.utc).isoformat(), **estado}); return
            if (carpeta / 'detener').exists():
                guardar(control / 'estado.json', {'estado': 'detenido'}); return
            print(json.dumps({'evento': 'reintento', 'intento': intento, 'codigo': proceso.returncode}), flush=True)
            time.sleep(60)
        guardar(control / 'estado.json', {'estado': 'requiere_revision', 'intentos': args.intentos})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
