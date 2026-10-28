"""Las migraciones amplían el esquema sin inscribir ni borrar el historial."""
from datetime import timedelta
import uuid

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class MigracionConservaHistorialTests(TransactionTestCase):
    def test_historial_y_fechas_anteriores_no_se_borran_ni_reciben_caducidad(self):
        anteriores = [('usuarios', '0002_origen_datos'), ('chat', '0001_initial'), ('sesiones', '0001_initial')]
        executor = MigrationExecutor(connection)
        actuales = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(anteriores)
            apps = executor.loader.project_state(anteriores).apps
            usuario = apps.get_model('auth', 'User').objects.create(username='migracion-sintetica')
            apps.get_model('usuarios', 'Perfil').objects.create(usuario_id=usuario.pk)
            inicio = timezone.now() - timedelta(days=50)
            fin = inicio + timedelta(days=7)
            sesion = apps.get_model('sesiones', 'SesionSemanal').objects.create(
                usuario_id=usuario.pk, numero=1, inicio=inicio, fin=fin, estado='cerrada',
            )
            identificador = uuid.uuid4()
            apps.get_model('chat', 'Mensaje').objects.create(
                id=identificador, usuario_id=usuario.pk, sesion_id=sesion.pk,
                contenido='Historial sintético anterior que se debe conservar.',
                remitente='usuario', fecha=inicio,
            )
            executor = MigrationExecutor(connection)
            executor.migrate(actuales)
            from chat.models import Mensaje
            from sesiones.models import SesionSemanal
            from usuarios.models import Perfil
            mensaje = Mensaje.objects.get(pk=identificador)
            self.assertEqual(mensaje.contenido, 'Historial sintético anterior que se debe conservar.')
            self.assertEqual(mensaje.fecha, inicio)
            self.assertIsNone(mensaje.eliminar_despues_de)
            self.assertEqual(mensaje.retencion_version, '')
            self.assertIsNone(Perfil.objects.get(usuario_id=usuario.pk).terminos_aceptados_en)
            conservada = SesionSemanal.objects.get(pk=sesion.pk)
            self.assertEqual((conservada.inicio, conservada.fin), (inicio, fin))
        finally:
            MigrationExecutor(connection).migrate(actuales)
