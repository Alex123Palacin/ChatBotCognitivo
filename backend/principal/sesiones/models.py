from django.conf import settings
from django.db import models


class SesionSemanal(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='semanas')
    numero = models.PositiveSmallIntegerField()
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=10, default='pendiente', choices=[('pendiente', 'Pendiente'), ('activa', 'Activa'), ('cerrada', 'Cerrada')])

    class Meta:
        ordering = ['numero']
        constraints = [models.UniqueConstraint(fields=['usuario', 'numero'], name='semana_unica_por_estudiante')]

    def __str__(self):
        return f'{self.usuario.email}: semana {self.numero}'
