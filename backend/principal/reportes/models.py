from django.db import models


class Evidencia(models.Model):
    mensaje = models.ForeignKey('chat.Mensaje', on_delete=models.CASCADE, related_name='evidencias')
    indicador = models.CharField(max_length=35)
    cita = models.TextField()
    observacion = models.TextField()
    senal = models.CharField(max_length=20)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['mensaje', 'indicador', 'cita'], name='evidencia_sin_duplicados')]


class ReporteSemanal(models.Model):
    sesion = models.OneToOneField('sesiones.SesionSemanal', on_delete=models.CASCADE, related_name='reporte')
    estado = models.CharField(max_length=10, default='pendiente')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    resumen = models.TextField(blank=True)
    nota = models.TextField(blank=True)
    mensajes_estudiante = models.PositiveIntegerField(default=0)
    total_evidencias = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sesion__numero']
