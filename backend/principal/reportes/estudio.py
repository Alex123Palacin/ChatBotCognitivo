"""Muestra fija: su selección no depende de resultados ni se repite al consultar."""
from django.db.models import Q

from .models import MuestraEstudio

CLAVE_ESTUDIO = 'estudio-20260911'


def muestra_actual():
    return MuestraEstudio.objects.filter(pk=CLAVE_ESTUDIO).first()


def muestra_json(muestra):
    if muestra is None:
        return None
    return {'clave': muestra.pk, 'seleccionados': muestra.usuarios.count(),
            'tamano': muestra.tamano, 'poblacion': len(muestra.poblacion_ids),
            'metodo': muestra.metodo, 'inicio': muestra.inicio.isoformat(),
            'fin': muestra.fin.isoformat(), 'creada': muestra.creada.isoformat()}


def acotar_mensajes(registros, muestra=None):
    muestra = muestra if muestra is not None else muestra_actual()
    if muestra is None:
        return registros
    # Los historiales personales se conservan completos; solo se delimita el análisis.
    return registros.filter(~Q(usuario__muestras_estudio=muestra)
                            | Q(fecha__gte=muestra.inicio, fecha__lt=muestra.fin)).distinct()
