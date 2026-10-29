"""Servidor de revisión: no crea ni modifica cuentas administrativas al arrancar."""
from pathlib import Path
import os
import sys

RAIZ = Path(__file__).resolve().parents[2]
ESPERADA = RAIZ / 'entregas_locales/actividad_20260911/actividad_local.sqlite3'
actual = Path(os.environ.get('DJANGO_DB_PATH', '')).resolve()
if actual != ESPERADA.resolve() or not actual.is_file():
    raise SystemExit('Selecciona primero la base aislada de actividad local.')
sys.path.insert(0, str(RAIZ / 'backend/principal'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'principal.settings')
import django
django.setup()
from django.core.management.commands.runserver import Command

Command().run_from_argv(['manage.py', 'runserver', '127.0.0.1:8021', '--noreload'])
