import json
import sqlite3
import threading
import time
from collections.abc import Callable

_TABLAS = """
CREATE TABLE IF NOT EXISTS tareas (
    id TEXT PRIMARY KEY,
    tarea TEXT NOT NULL,
    canal TEXT NOT NULL,
    solicitante TEXT,
    estado TEXT NOT NULL,
    subestado TEXT,
    resumen TEXT NOT NULL DEFAULT '',
    pregunta TEXT,
    creada REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS eventos (
    task_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (task_id, seq)
);
"""


class Store:
    """Tareas y eventos en SQLite. Nunca recibe la contraseña del escritorio."""

    def __init__(self, ruta: str, on_evento: Callable[[str], None] | None = None) -> None:
        # on_evento(task_id) se llama después de guardar (commit) cada evento nuevo.
        self._on_evento = on_evento
        self._con = sqlite3.connect(ruta, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._con.executescript(_TABLAS)

    def crear_tarea(self, task_id: str, tarea: str, canal: str, solicitante: str | None) -> None:
        with self._lock, self._con:
            self._con.execute(
                "INSERT INTO tareas (id, tarea, canal, solicitante, estado, creada)"
                " VALUES (?, ?, ?, ?, 'en_curso', ?)",
                (task_id, tarea, canal, solicitante, time.time()),
            )

    def obtener(self, task_id: str) -> dict | None:
        with self._lock:
            fila = self._con.execute("SELECT * FROM tareas WHERE id = ?", (task_id,)).fetchone()
        if fila is None:
            return None
        tarea = dict(fila)
        tarea["pregunta"] = json.loads(tarea["pregunta"]) if tarea["pregunta"] else None
        return tarea

    def agregar_evento(self, task_id: str, event: str, data: dict) -> int:
        with self._lock, self._con:
            seq = self._agregar_evento(task_id, event, data)
        self._notificar(task_id)
        return seq

    def eventos_desde(self, task_id: str, seq: int = 0) -> list[dict]:
        with self._lock:
            filas = self._con.execute(
                "SELECT seq, event, data FROM eventos WHERE task_id = ? AND seq > ? ORDER BY seq",
                (task_id, seq),
            ).fetchall()
        return [
            {"seq": f["seq"], "event": f["event"], "data": json.loads(f["data"])} for f in filas
        ]

    def finalizar(self, task_id: str, estado: str, resumen: str) -> None:
        """Cierra la tarea y deja el evento `fin`, todo en una sola transacción."""
        with self._lock, self._con:
            self._con.execute(
                "UPDATE tareas SET estado = ?, subestado = NULL, pregunta = NULL, resumen = ?"
                " WHERE id = ?",
                (estado, resumen, task_id),
            )
            self._agregar_evento(task_id, "fin", {"estado": estado, "resumen": resumen})
        self._notificar(task_id)

    def registrar_pregunta(self, task_id: str, event: str, data: dict) -> None:
        """Guarda la pregunta vigente y pasa a `en_espera`; todo en una transacción.

        `event` es `pregunta` o `confirmacion`; `data` trae `pregunta_id` (contrato §2).
        """
        with self._lock, self._con:
            self._con.execute(
                "UPDATE tareas SET subestado = 'en_espera', pregunta = ? WHERE id = ?",
                (json.dumps(data, ensure_ascii=False), task_id),
            )
            self._agregar_evento(task_id, event, data)
            self._agregar_evento(
                task_id, "estado", {"estado": "en_curso", "subestado": "en_espera"}
            )
        self._notificar(task_id)

    def consumir_pregunta(
        self, task_id: str, pregunta_id: str, validar: Callable[[dict], None]
    ) -> bool:
        """Cierra la pregunta si `pregunta_id` es la vigente. La primera respuesta gana.

        `validar(pregunta)` puede lanzar para rechazar el valor sin consumir la pregunta.
        Devuelve False si no hay pregunta vigente o es otra.
        """
        with self._lock, self._con:
            fila = self._con.execute(
                "SELECT pregunta FROM tareas WHERE id = ? AND estado = 'en_curso'", (task_id,)
            ).fetchone()
            pregunta = json.loads(fila["pregunta"]) if fila and fila["pregunta"] else None
            if pregunta is None or pregunta.get("pregunta_id") != pregunta_id:
                return False
            validar(pregunta)
            self._con.execute(
                "UPDATE tareas SET subestado = NULL, pregunta = NULL WHERE id = ?", (task_id,)
            )
            self._agregar_evento(task_id, "estado", {"estado": "en_curso"})
        self._notificar(task_id)
        return True

    def marcar_huerfanas_fallidas(self) -> int:
        """Al arrancar: lo que quedó `en_curso` ya no tiene worker."""
        with self._lock:
            ids = [
                f["id"]
                for f in self._con.execute("SELECT id FROM tareas WHERE estado = 'en_curso'")
            ]
        for task_id in ids:
            self.finalizar(task_id, "fallida", "Servicio reiniciado antes de terminar la tarea.")
        return len(ids)

    def _notificar(self, task_id: str) -> None:
        if self._on_evento is not None:
            self._on_evento(task_id)

    def _agregar_evento(self, task_id: str, event: str, data: dict) -> int:
        seq = self._con.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM eventos WHERE task_id = ?", (task_id,)
        ).fetchone()[0]
        self._con.execute(
            "INSERT INTO eventos (task_id, seq, event, data) VALUES (?, ?, ?, ?)",
            (task_id, seq, event, json.dumps(data, ensure_ascii=False)),
        )
        return seq
