import hmac
import json
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, SecretStr, StringConstraints, field_validator

from app.bus import Bus, Respuestas
from app.config import Settings
from app.cuadros import Cuadros
from app.errors import ApiError, instalar_handlers
from app.store import Store
from app.worker import Coordinador


class Escritorio(BaseModel):
    url: str
    password: SecretStr

    @field_validator("url")
    @classmethod
    def _solo_wss(cls, v: str) -> str:
        if not v.startswith("wss://") or len(v) <= len("wss://"):
            raise ValueError("debe ser una URL wss://")
        return v

    @field_validator("password")
    @classmethod
    def _no_vacia(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value():
            raise ValueError("no puede ir vacía")
        return v


class NuevaTarea(BaseModel):
    tarea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    escritorio: Escritorio
    canal: Literal["api", "chat"] = "api"
    solicitante: Annotated[str, StringConstraints(max_length=100)] | None = None


class TareaCreada(BaseModel):
    task_id: str


class RespuestaPregunta(BaseModel):
    pregunta_id: str
    tipo: Literal["eleccion", "confirmacion"]
    valor: str | bool


def _validar_valor(cuerpo: RespuestaPregunta, pregunta: dict) -> None:
    if cuerpo.tipo != pregunta.get("tipo"):
        raise ApiError(422, "entrada_invalida", "tipo: no coincide con la pregunta vigente.")
    if cuerpo.tipo == "confirmacion":
        if not isinstance(cuerpo.valor, bool):
            raise ApiError(422, "entrada_invalida", "valor: debe ser true o false.")
    else:
        ids = {c.get("id") for c in pregunta.get("candidatos", [])}
        if not isinstance(cuerpo.valor, str) or cuerpo.valor not in ids:
            raise ApiError(422, "entrada_invalida", "valor: no es un candidato de la pregunta.")


class EstadoTarea(BaseModel):
    estado: Literal["en_curso", "terminada", "fallida"]
    resumen: str
    subestado: Literal["en_espera"] | None = None
    pregunta: dict | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.desde_entorno()
    if not settings.api_token:
        raise RuntimeError("Falta API_TOKEN: sin token todas las rutas quedarían abiertas.")

    bus = Bus()
    respuestas = Respuestas()
    cuadros = Cuadros(settings.cuadros_dir)
    store = Store(settings.db_path, on_evento=bus.publicar)
    coordinador = Coordinador(store, settings.worker_demora)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.marcar_huerfanas_fallidas()
        yield

    def exigir_token(request: Request) -> None:
        esquema, _, token = request.headers.get("authorization", "").partition(" ")
        valido = esquema.lower() == "bearer" and hmac.compare_digest(
            token.encode(), settings.api_token.encode()
        )
        if not valido:
            raise ApiError(401, "no_autorizado", "Falta el token del equipo o no es válido.")

    app = FastAPI(title="Navegante", lifespan=lifespan, dependencies=[Depends(exigir_token)])
    instalar_handlers(app)
    # Ganchos para B3: publicar con store.agregar_evento / registrar_pregunta / finalizar,
    # guardar cuadros con cuadros.*, y esperar la respuesta con respuestas.esperar.
    app.state.store, app.state.bus = store, bus
    app.state.respuestas, app.state.cuadros = respuestas, cuadros

    def existe(task_id: str) -> None:
        if store.obtener(task_id) is None:
            raise ApiError(404, "tarea_no_existe", "No existe una tarea con ese id.")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.post("/tasks", response_model=TareaCreada)
    async def crear_tarea(cuerpo: NuevaTarea) -> TareaCreada:
        task_id = uuid.uuid4().hex
        store.crear_tarea(task_id, cuerpo.tarea, cuerpo.canal, cuerpo.solicitante)
        coordinador.lanzar(task_id, cuerpo.escritorio.url, cuerpo.escritorio.password)
        return TareaCreada(task_id=task_id)

    @app.get("/tasks/{task_id}", response_model=EstadoTarea, response_model_exclude_none=True)
    async def ver_tarea(task_id: str) -> dict:
        tarea = store.obtener(task_id)
        if tarea is None:
            raise ApiError(404, "tarea_no_existe", "No existe una tarea con ese id.")
        return tarea

    @app.get("/tasks/{task_id}/eventos")
    async def eventos(task_id: str, request: Request) -> StreamingResponse:
        existe(task_id)
        try:
            desde = max(0, int(request.headers.get("last-event-id", "0")))
        except ValueError:
            desde = 0

        async def flujo():
            nonlocal desde
            with bus.suscribir(task_id) as sub:
                while True:
                    # Se relee la tabla tras cada aviso: no hay hueco entre repetición y vivo.
                    for ev in store.eventos_desde(task_id, desde):
                        desde = ev["seq"]
                        datos = json.dumps(ev["data"], ensure_ascii=False)
                        yield f"id: {ev['seq']}\nevent: {ev['event']}\ndata: {datos}\n\n"
                        if ev["event"] == "fin":
                            return
                    if not await sub.esperar(settings.sse_latido):
                        yield ": latido\n\n"

        cabeceras = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return StreamingResponse(flujo(), media_type="text/event-stream", headers=cabeceras)

    @app.post("/tasks/{task_id}/respuesta", status_code=202)
    async def responder(task_id: str, cuerpo: RespuestaPregunta) -> dict:
        existe(task_id)
        vigente = store.consumir_pregunta(
            task_id, cuerpo.pregunta_id, lambda p: _validar_valor(cuerpo, p)
        )
        if not vigente:
            raise ApiError(409, "pregunta_no_vigente", "Esa pregunta ya no está vigente.")
        respuestas.entregar(task_id, {"pregunta_id": cuerpo.pregunta_id, "valor": cuerpo.valor})
        return {"ok": True}

    @app.get("/tasks/{task_id}/pantalla.jpg")
    async def pantalla(task_id: str) -> Response:
        existe(task_id)
        jpeg = cuadros.pantalla(task_id)
        if jpeg is None:
            return Response(status_code=204)
        return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/tasks/{task_id}/capturas/{n}.jpg")
    async def captura(task_id: str, n: int) -> Response:
        existe(task_id)
        jpeg = cuadros.captura(task_id, n)
        if jpeg is None:
            raise ApiError(404, "tarea_no_existe", "No existe esa captura.")
        return Response(jpeg, media_type="image/jpeg")

    return app
