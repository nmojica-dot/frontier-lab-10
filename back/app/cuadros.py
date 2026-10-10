"""Cuadros del escritorio: el último en memoria, las capturas de pasos en disco."""

from pathlib import Path

_JPEG = b"\xff\xd8\xff"


def _validar(jpeg: bytes) -> None:
    if not jpeg.startswith(_JPEG):
        raise ValueError("el cuadro no es un JPEG")


class Cuadros:
    def __init__(self, carpeta: str) -> None:
        self._carpeta = Path(carpeta)
        self._ultimo: dict[str, bytes] = {}

    def guardar_pantalla(self, task_id: str, jpeg: bytes) -> None:
        """Gancho para B2/B3: llamar con cada cuadro nuevo (ya codificado a JPEG)."""
        _validar(jpeg)
        self._ultimo[task_id] = jpeg

    def pantalla(self, task_id: str) -> bytes | None:
        return self._ultimo.get(task_id)

    def guardar_captura(self, task_id: str, n: int, jpeg: bytes) -> None:
        """Gancho para B3: guardar la captura `n` antes de emitir `paso`/`evidencia`."""
        _validar(jpeg)
        destino = self._carpeta / task_id / f"{n}.jpg"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(jpeg)

    def captura(self, task_id: str, n: int) -> bytes | None:
        ruta = self._carpeta / task_id / f"{n}.jpg"
        return ruta.read_bytes() if ruta.is_file() else None

    def olvidar_pantalla(self, task_id: str) -> None:
        self._ultimo.pop(task_id, None)
