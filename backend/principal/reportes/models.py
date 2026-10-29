from django.db import models
from django.conf import settings


class MuestraEstudio(models.Model):
    clave = models.SlugField(primary_key=True, max_length=60)
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    tamano = models.PositiveSmallIntegerField(default=110)
    poblacion_ids = models.JSONField(default=list)
    metodo = models.CharField(max_length=80, default='aleatorio_simple_sin_reemplazo')
    creada = models.DateTimeField(auto_now_add=True)
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='muestras_estudio')


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
