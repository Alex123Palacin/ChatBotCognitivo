import uuid

from django.conf import settings
from django.db import models


class MensajesQuerySet(models.QuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        objs = list(objs)
        for mensaje in objs:
            mensaje.preparar_retencion()
        return super().bulk_create(objs, *args, **kwargs)


class Mensaje(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mensajes_chat')
    sesion = models.ForeignKey('sesiones.SesionSemanal', on_delete=models.CASCADE, related_name='mensajes')
    contenido = models.TextField()
    remitente = models.CharField(max_length=10, choices=[('usuario', 'Estudiante'), ('asistente', 'Asistente')])
    fecha = models.DateTimeField()
    clave_envio = models.UUIDField(null=True, blank=True)
    respuesta_a = models.OneToOneField('self', null=True, blank=True, on_delete=models.CASCADE, related_name='respuesta')
    respuesta_error = models.TextField(blank=True)
    analisis_estado = models.CharField(max_length=12, default='pendiente')
    analisis_hasta = models.DateTimeField(null=True, blank=True)
    analisis_intentos = models.PositiveIntegerField(default=0)
    # NULL identifica datos heredados que esta política no inscribe ni elimina.
    eliminar_despues_de = models.DateTimeField(null=True, blank=True, db_index=True)
    retencion_version = models.CharField(max_length=60, blank=True)

    objects = MensajesQuerySet.as_manager()

    def preparar_retencion(self):
        if not self._state.adding or self.eliminar_despues_de is not None or not self.usuario_id or not self.fecha:
            return
        from usuarios.models import Perfil
        from usuarios.retencion import VERSION_TERMINOS, fecha_eliminacion

        perfil = Perfil.objects.filter(usuario_id=self.usuario_id).first()
        if perfil is not None:
            fecha = self._meta.get_field('fecha').to_python(self.fecha)
            self.eliminar_despues_de = fecha_eliminacion(fecha, perfil)
            if self.eliminar_despues_de is not None:
                self.retencion_version = VERSION_TERMINOS

    def save(self, *args, **kwargs):
        self.preparar_retencion()
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['fecha', 'id']
        constraints = [models.UniqueConstraint(fields=['usuario', 'clave_envio'], name='envio_unico_por_estudiante')]
