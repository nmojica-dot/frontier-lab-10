"""Piezas compartidas del agente (B3). Todo lo que habla con el modelo pasa por `Modelo`."""

from dataclasses import dataclass
from typing import Any, Protocol


class ErrorModelo(Exception):
    """El modelo no respondió algo utilizable (red, formato, proveedor)."""


class TopeDeCosto(ErrorModelo):
    """Se alcanzó el tope de dólares por tarea; la tarea debe terminar `fallida`."""


@dataclass(frozen=True)
class RespuestaModelo:
    datos: dict[str, Any]  # JSON ya validado contra el esquema pedido
    costo: float  # dólares de esta llamada
    tokens_entrada: int = 0
    tokens_salida: int = 0


class Modelo(Protocol):
    """Una llamada al modelo con salida JSON. La implementación real usa OpenRouter;
    los tests usan un modelo falso con respuestas fijas."""

    async def pedir_json(
        self,
        *,
        sistema: str,
        usuario: str,
        esquema: dict[str, Any],
        imagen_png: bytes | None = None,
    ) -> RespuestaModelo: ...
