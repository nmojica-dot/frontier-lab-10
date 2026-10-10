"""Contrato mínimo entre B3 (ciclo del agente) y B4 (criterio).

B3 aún no existe, así que este módulo fija lo que B4 necesita recibir. Todo es
puro: sin red, sin modelo, sin reloj. B3 debe entregar:

1. `ContratoCambios`, armado desde la instrucción ANTES de mirar la app y
   congelado. B4 nunca lo modifica ni lo amplía con texto que salga de la app.
2. Por cada acción que el modelo propone, una `Accion` ya normalizada.
3. `EstadoCriterio` con lo verificado hasta ese momento: cuántos registros
   coinciden con el objetivo, qué compromisos ya se intentaron y si la persona
   ya confirmó una eliminación. Un compromiso se registra en `compromisos`
   ANTES de ejecutarlo: un intento sin confirmar cuenta como hecho y no se
   reintenta a ciegas.
4. Al final, la evidencia y los bloqueos, para decidir el estado y armar el
   resumen (ver `estado.py` y `resumen.py`).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Verbo = Literal["guardar", "exportar", "eliminar"]
Origen = Literal["chat", "api"]
TipoAccion = Literal["leer", "navegar", "escribir", "comprometer"]


class _Modelo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContratoCambios(_Modelo):
    """Qué puede cambiar esta tarea. Sale solo de la instrucción de la persona."""

    # Datos de la instrucción que identifican el registro (p. ej. documento).
    registro_objetivo: dict[str, str] = {}
    # campo -> valores que se pueden escribir: literal de la instrucción, opción
    # de lista que le corresponde o valor calculado. B3 los resuelve antes.
    valores_permitidos: dict[str, tuple[str, ...]] = {}
    verbos_permitidos: frozenset[Verbo] = frozenset()
    # Pregunta a responder, si la instrucción es una consulta.
    pregunta: str | None = None
    # La tarea crea un registro nuevo: guardar exige haber comprobado que NO existe.
    crea: bool = False


class Accion(_Modelo):
    tipo: TipoAccion
    campo: str | None = None  # para "escribir"
    valor: str | None = None  # para "escribir"
    verbo: Verbo | None = None  # para "comprometer"
    # Cuántos registros tocaría un "eliminar". None = no se sabe.
    registros_afectados: int | None = None


class EstadoCriterio(_Modelo):
    # Registros que coinciden con el objetivo tras reabrir/buscar. None = sin verificar.
    registros_coincidentes: int | None = None
    compromisos: tuple[Verbo, ...] = ()
    eliminacion_confirmada: bool = False


Resultado = Literal["permitida", "denegada", "pregunta", "confirmacion"]


class Decision(_Modelo):
    """`fallida=True` significa que la tarea debe cerrar `fallida` con `motivo`."""

    resultado: Resultado
    motivo: str = ""
    fallida: bool = False

    @property
    def permitida(self) -> bool:
        return self.resultado == "permitida"
