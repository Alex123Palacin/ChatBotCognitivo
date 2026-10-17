import uuid

from django.conf import settings
from django.db import models


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

    class Meta:
        ordering = ['fecha', 'id']
        constraints = [models.UniqueConstraint(fields=['usuario', 'clave_envio'], name='envio_unico_por_estudiante')]
