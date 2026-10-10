"""Cliente de OpenRouter que implementa `Modelo` (chat completions con salida JSON estricta)."""

import base64
import json
import os
from typing import Any

import httpx

from app.agente.tipos import ErrorModelo, RespuestaModelo, TopeDeCosto

URL_BASE = "https://openrouter.ai/api/v1"

# Id verificado el 2026-10-10 contra https://openrouter.ai/api/v1/models (entrada de imagen).
# Se sobreescribe con la variable MODELO_ID (o el parámetro `modelo_id`).
MODELO_ID_DEFECTO = "anthropic/claude-sonnet-5.5"


class ClienteOpenRouter:
    """Una instancia por tarea: acumula el costo real y corta al pasar `costo_max`."""

    def __init__(
        self,
        api_key: str,
        *,
        modelo_id: str | None = None,
        proveedores: list[str] | None = None,
        costo_max: float = 0.50,
        timeout: float = 60.0,
        base_url: str = URL_BASE,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("falta la llave de OpenRouter")
        self.__api_key = api_key
        self.modelo_id = modelo_id or os.environ.get("MODELO_ID") or MODELO_ID_DEFECTO
        self.proveedores = proveedores
        self.costo_max = costo_max
        self.costo_acumulado = 0.0
        self._timeout = timeout
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def __repr__(self) -> str:
        return f"ClienteOpenRouter(modelo_id={self.modelo_id!r}, proveedores={self.proveedores!r})"

    def _cuerpo(
        self, sistema: str, usuario: str, esquema: dict[str, Any], imagen_png: bytes | None
    ) -> dict[str, Any]:
        contenido: list[dict[str, Any]] = [{"type": "text", "text": usuario}]
        if imagen_png is not None:
            b64 = base64.b64encode(imagen_png).decode("ascii")
            url = f"data:image/png;base64,{b64}"
            contenido.append({"type": "image_url", "image_url": {"url": url}})
        cuerpo: dict[str, Any] = {
            "model": self.modelo_id,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": contenido},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "respuesta", "strict": True, "schema": esquema},
            },
            "usage": {"include": True},
        }
        if self.proveedores:
            cuerpo["provider"] = {"order": self.proveedores, "allow_fallbacks": False}
        return cuerpo

    async def _enviar(self, cuerpo: dict[str, Any]) -> httpx.Response:
        """POST con 1 reintento solo ante error de red o 5xx."""
        cabeceras = {"Authorization": f"Bearer {self.__api_key}"}
        ultimo = "sin intentos"
        for _ in range(2):
            try:
                async with httpx.AsyncClient(
                    transport=self._transport, timeout=self._timeout
                ) as http:
                    resp = await http.post(
                        f"{self._base_url}/chat/completions", json=cuerpo, headers=cabeceras
                    )
            except httpx.TransportError as e:
                # Solo el tipo: el texto de la excepción podría arrastrar datos de la petición.
                ultimo = f"error de red ({type(e).__name__})"
                continue
            if resp.status_code >= 500:
                ultimo = f"OpenRouter respondió {resp.status_code}"
                continue
            return resp
        raise ErrorModelo(f"{ultimo} tras reintentar")

    async def pedir_json(
        self,
        *,
        sistema: str,
        usuario: str,
        esquema: dict[str, Any],
        imagen_png: bytes | None = None,
    ) -> RespuestaModelo:
        if self.costo_acumulado >= self.costo_max:
            raise TopeDeCosto(
                f"tope de costo alcanzado: {self.costo_acumulado:.4f} de {self.costo_max:.4f} USD"
            )
        resp = await self._enviar(self._cuerpo(sistema, usuario, esquema, imagen_png))
        if resp.status_code >= 400:
            raise ErrorModelo(f"OpenRouter rechazó la petición ({resp.status_code})")
        try:
            cuerpo = resp.json()
        except ValueError as e:
            raise ErrorModelo("respuesta de OpenRouter que no es JSON") from e

        usage = cuerpo.get("usage") if isinstance(cuerpo, dict) else None
        costo = usage.get("cost") if isinstance(usage, dict) else None
        if not isinstance(costo, int | float) or isinstance(costo, bool):
            raise ErrorModelo("la respuesta no trae usage.cost")
        self.costo_acumulado += float(costo)

        datos = self._extraer(cuerpo)
        if self.costo_acumulado > self.costo_max:
            raise TopeDeCosto(
                f"tope de costo superado: {self.costo_acumulado:.4f} de {self.costo_max:.4f} USD"
            )
        return RespuestaModelo(
            datos=datos,
            costo=float(costo),
            tokens_entrada=int(usage.get("prompt_tokens") or 0),
            tokens_salida=int(usage.get("completion_tokens") or 0),
        )

    @staticmethod
    def _extraer(cuerpo: dict[str, Any]) -> dict[str, Any]:
        try:
            texto = cuerpo["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErrorModelo("respuesta sin choices[0].message.content") from e
        if not isinstance(texto, str) or not texto.strip():
            raise ErrorModelo("el modelo devolvió una respuesta vacía")
        try:
            datos = json.loads(texto)
        except ValueError as e:
            raise ErrorModelo("el modelo devolvió JSON inválido") from e
        if not isinstance(datos, dict):
            raise ErrorModelo("el modelo devolvió JSON que no es un objeto")
        return datos
