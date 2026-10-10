"""B4: criterio, verificación y resumen. Solo funciones puras; B3 las llama."""

from app.criterio.contrato import (
    Accion,
    ContratoCambios,
    Decision,
    EstadoCriterio,
)
from app.criterio.estado import EntradaEstado, Evidencia, ResultadoEstado, decidir_estado
from app.criterio.redaccion import SecretoSinRedactar, redactar, redactar_datos
from app.criterio.resumen import EntradaResumen, armar_resumen, linea_respuesta
from app.criterio.seguridad import desempatar, detectar_ordenes, validar_accion

__all__ = [
    "Accion",
    "ContratoCambios",
    "Decision",
    "EntradaEstado",
    "EntradaResumen",
    "EstadoCriterio",
    "Evidencia",
    "ResultadoEstado",
    "SecretoSinRedactar",
    "armar_resumen",
    "decidir_estado",
    "desempatar",
    "detectar_ordenes",
    "linea_respuesta",
    "redactar",
    "redactar_datos",
    "validar_accion",
]
