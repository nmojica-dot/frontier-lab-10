import asyncio
import hashlib
import logging
from collections.abc import Awaitable, Callable

from pydantic import SecretStr

from app.store import Store

log = logging.getLogger("navegante.worker")

# (task_id, instruccion, canal, url, password). El ejecutor real deja el estado final en el
# store y no lanza; si no hay ejecutor, corre el worker de mentira.
Ejecutor = Callable[[str, str, str, str, SecretStr], Awaitable[None]]

RESUMEN_ESQUELETO = (
    "El agente todavía no está conectado al escritorio: la tarea no se ejecutó y no se cambió nada."
)


class Coordinador:
    """Lanza un worker por tarea y deja una sola activa por escritorio.

    Si llega otra al mismo escritorio, espera su turno. Por ahora el worker es de
    mentira: emite los eventos del contrato y termina `fallida`, nunca `terminada`,
    porque no hizo nada que se pueda comprobar.
    """

    def __init__(self, store: Store, demora: float, ejecutor: Ejecutor | None = None) -> None:
        self._store = store
        self._demora = demora
        self._ejecutor = ejecutor
        self._turnos: dict[str, asyncio.Lock] = {}
        self._vivas: set[asyncio.Task] = set()

    def lanzar(
        self, task_id: str, instruccion: str, canal: str, url: str, password: SecretStr
    ) -> None:
        tarea = asyncio.create_task(self._correr(task_id, instruccion, canal, url, password))
        self._vivas.add(tarea)
        tarea.add_done_callback(self._vivas.discard)

    async def _correr(
        self, task_id: str, instruccion: str, canal: str, url: str, password: SecretStr
    ) -> None:
        # La contraseña llega solo hasta aquí, en memoria.
        # La clave es un hash: la URL del escritorio podría llevar un token.
        clave = hashlib.sha256(url.encode()).hexdigest()
        turno = self._turnos.setdefault(clave, asyncio.Lock())
        try:
            async with turno:
                if self._ejecutor is not None:
                    await self._ejecutor(task_id, instruccion, canal, url, password)
                    return
                self._store.agregar_evento(task_id, "estado", {"estado": "en_curso"})
                self._store.agregar_evento(
                    task_id,
                    "paso",
                    {"n": 1, "texto": "Recibí la tarea. Todavía no opero el escritorio."},
                )
                await asyncio.sleep(self._demora)
                self._store.finalizar(task_id, "fallida", RESUMEN_ESQUELETO)
        except Exception as exc:  # noqa: BLE001 - se reporta como fallida, no se traga
            log.error("worker falló task=%s tipo=%s", task_id, type(exc).__name__)
            self._store.finalizar(task_id, "fallida", "Error interno del servicio.")
