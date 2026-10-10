import hmac
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, SecretStr, StringConstraints, field_validator

from app.config import Settings
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


class EstadoTarea(BaseModel):
    estado: Literal["en_curso", "terminada", "fallida"]
    resumen: str
    subestado: Literal["en_espera"] | None = None
    pregunta: dict | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.desde_entorno()
    if not settings.api_token:
        raise RuntimeError("Falta API_TOKEN: sin token todas las rutas quedarían abiertas.")

    store = Store(settings.db_path)
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

    return app
