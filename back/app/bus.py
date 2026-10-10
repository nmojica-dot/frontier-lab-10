"""Publicación de eventos a los suscriptores SSE y entrega de respuestas al worker.

La fuente de verdad de los eventos es la tabla `eventos`. El bus solo despierta a
quien está escuchando para que relea la tabla; así no se pierde ni se duplica nada.
"""

import asyncio
from collections import defaultdict
from typing import Self


class Suscripcion:
    def __init__(self, bus: "Bus", task_id: str) -> None:
        self._bus = bus
        self.task_id = task_id
        self._loop = asyncio.get_running_loop()
        self._aviso = asyncio.Event()

    def despertar(self) -> None:
        self._loop.call_soon_threadsafe(self._aviso.set)

    async def esperar(self, timeout: float) -> bool:
        """True si hubo aviso; False si pasó `timeout` sin novedades."""
        try:
            await asyncio.wait_for(self._aviso.wait(), timeout)
        except TimeoutError:
            return False
        self._aviso.clear()
        return True

    def __enter__(self) -> Self:
        self._bus._alta(self)
        return self

    def __exit__(self, *_: object) -> None:
        self._bus._baja(self)


class Bus:
    def __init__(self) -> None:
        self._subs: dict[str, set[Suscripcion]] = defaultdict(set)

    def suscribir(self, task_id: str) -> Suscripcion:
        return Suscripcion(self, task_id)

    def publicar(self, task_id: str) -> None:
        """Gancho de `Store(on_evento=...)`. Seguro desde cualquier hilo."""
        for sub in list(self._subs.get(task_id, ())):
            sub.despertar()

    def n_suscriptores(self, task_id: str) -> int:
        return len(self._subs.get(task_id, ()))

    def _alta(self, sub: Suscripcion) -> None:
        self._subs[sub.task_id].add(sub)

    def _baja(self, sub: Suscripcion) -> None:
        self._subs[sub.task_id].discard(sub)
        if not self._subs[sub.task_id]:
            del self._subs[sub.task_id]


class Respuestas:
    """Buzón por tarea: el endpoint deja la respuesta, el worker (B3) la espera.

    El worker llama `await respuestas.esperar(task_id)` después de
    `store.registrar_pregunta(...)`. Si la respuesta llega antes, queda guardada.
    """

    def __init__(self) -> None:
        self._colas: dict[str, asyncio.Queue[dict]] = {}

    def entregar(self, task_id: str, respuesta: dict) -> None:
        self._cola(task_id).put_nowait(respuesta)

    async def esperar(self, task_id: str) -> dict:
        return await self._cola(task_id).get()

    def olvidar(self, task_id: str) -> None:
        self._colas.pop(task_id, None)

    def _cola(self, task_id: str) -> "asyncio.Queue[dict]":
        return self._colas.setdefault(task_id, asyncio.Queue())
