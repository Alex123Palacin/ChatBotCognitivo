"""Muestra fija: su selección no depende de resultados ni se repite al consultar."""
from django.db.models import Q

from .models import MuestraEstudio

# Identidad histórica estable: corregir las fechas no crea otra muestra ni otro sorteo.
CLAVE_ESTUDIO = 'estudio-20260911'


def muestra_actual():
    return MuestraEstudio.objects.filter(pk=CLAVE_ESTUDIO).first()


def muestra_valida(muestra):
    """No sustituye integrantes borrados ni admite cuentas ajenas a la selección."""
    if muestra is None or muestra.tamano != 110:
        return False
    poblacion = muestra.poblacion_ids
    if (not isinstance(poblacion, list) or any(type(pk) is not int for pk in poblacion)
            or len(poblacion) != 136 or len(set(poblacion)) != 136):
        return False
    integrantes = list(muestra.usuarios.values('pk', 'is_staff', 'is_superuser'))
    return (len(integrantes) == 110 and all(
        u['pk'] in poblacion and not u['is_staff'] and not u['is_superuser']
        for u in integrantes))


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
