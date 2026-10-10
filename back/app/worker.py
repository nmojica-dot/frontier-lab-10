import asyncio
import logging

from pydantic import SecretStr

from app.store import Store

log = logging.getLogger("navegante.worker")

RESUMEN_ESQUELETO = (
    "El agente todavía no está conectado al escritorio: la tarea no se ejecutó y no se cambió nada."
)


class Coordinador:
    """Lanza un worker por tarea y deja una sola activa por escritorio.

    Si llega otra al mismo escritorio, espera su turno. Por ahora el worker es de
    mentira: emite los eventos del contrato y termina `fallida`, nunca `terminada`,
    porque no hizo nada que se pueda comprobar.
    """

    def __init__(self, store: Store, demora: float) -> None:
        self._store = store
        self._demora = demora
        self._turnos: dict[str, asyncio.Lock] = {}
        self._vivas: set[asyncio.Task] = set()

    def lanzar(self, task_id: str, url: str, password: SecretStr) -> None:
        tarea = asyncio.create_task(self._correr(task_id, url, password))
        self._vivas.add(tarea)
        tarea.add_done_callback(self._vivas.discard)

    async def _correr(self, task_id: str, url: str, password: SecretStr) -> None:
        # La contraseña llega solo hasta aquí, en memoria. B2 la usará para conectar.
        turno = self._turnos.setdefault(url, asyncio.Lock())
        try:
            async with turno:
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
