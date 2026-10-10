from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str) -> None:
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje


def _respuesta(status: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"codigo": codigo, "mensaje": mensaje}}
    )


def instalar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _respuesta(exc.status, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Solo campo y motivo: el detalle por defecto de FastAPI repite el valor
        # recibido, y ahí puede venir la contraseña del escritorio.
        partes = []
        for e in exc.errors():
            campo = ".".join(str(p) for p in e["loc"] if p != "body") or "cuerpo"
            partes.append(f"{campo}: {e['msg']}")
        return _respuesta(422, "entrada_invalida", "; ".join(partes))
