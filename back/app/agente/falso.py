"""Modelo de mentira para los tests del agente: respuestas fijas, en orden."""

from typing import Any

from app.agente.tipos import ErrorModelo, RespuestaModelo


class ModeloFalso:
    def __init__(self, respuestas: list[dict[str, Any]], costo: float = 0.0) -> None:
        self._respuestas = list(respuestas)
        self.costo = costo
        self.llamadas: list[dict[str, Any]] = []

    async def pedir_json(
        self,
        *,
        sistema: str,
        usuario: str,
        esquema: dict[str, Any],
        imagen_png: bytes | None = None,
    ) -> RespuestaModelo:
        self.llamadas.append(
            {"sistema": sistema, "usuario": usuario, "esquema": esquema, "imagen_png": imagen_png}
        )
        if len(self.llamadas) > len(self._respuestas):
            raise ErrorModelo("ModeloFalso sin más respuestas")
        return RespuestaModelo(datos=self._respuestas[len(self.llamadas) - 1], costo=self.costo)
