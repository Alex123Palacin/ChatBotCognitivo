from django.conf import settings
from django.db import models


class Perfil(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    inicio_programa = models.DateTimeField(null=True, blank=True)
    ultima_actividad = models.DateTimeField(null=True, blank=True)
    conectado = models.BooleanField(default=False)
    respuesta_hasta = models.DateTimeField(null=True, blank=True)
    respuesta_token = models.CharField(max_length=36, blank=True)
    origen_datos = models.CharField(max_length=20, default='conversacion', choices=[('conversacion', 'Interacción registrada'), ('demostracion', 'Demostración')])
    terminos_version = models.CharField(max_length=60, blank=True)
    terminos_aceptados_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.usuario.username
