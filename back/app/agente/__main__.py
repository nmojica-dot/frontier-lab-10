"""Corre un caso de ejemplo contra el escritorio real, con el agente completo.

    ESCRITORIO_URL=wss://.../websockify ESCRITORIO_PASSWORD=... OPENROUTER_API_KEY=... \
    MODELO_ID=... ESCRITORIO_TOKEN=... \
        uv run python -m app.agente E5 [--sin-reset] [carpeta_pruebas]

`E5` es el id de un JSON de `pruebas/`; si no existe, el argumento se usa como la instrucción.
Con `ESCRITORIO_TOKEN` (el "token del escritorio" de la tarjeta) reinicia la app antes
(`/__reset`) y revisa el resultado después (`/__check`). Nada de esto imprime secretos.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx
from pydantic import SecretStr

from app.agente.ciclo import ejecutar_tarea
from app.agente.openrouter import ClienteOpenRouter
from app.cuadros import Cuadros
from app.store import Store

PRUEBAS = Path(__file__).resolve().parents[3] / "archivo/material-reto1/extraido/pruebas"


def _base_http(url_wss: str) -> str:
    return url_wss.replace("wss://", "https://", 1).removesuffix("/websockify")


def _cargar(arg: str, carpeta: Path) -> dict:
    for f in sorted(carpeta.glob(f"{arg}-*.json")):
        return json.loads(f.read_text(encoding="utf-8"))
    return {"id": "libre", "instruccion": arg}


def _llamar(metodo: str, url: str, token: str, cuerpo: dict | None = None) -> str:
    r = httpx.request(
        metodo,
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=cuerpo,
        timeout=60,
    )
    return f"{r.status_code} {r.text[:600]}"


async def main(arg: str, reset: bool, carpeta: Path) -> None:
    caso = _cargar(arg, carpeta)
    url = os.environ["ESCRITORIO_URL"]
    token = os.environ.get("ESCRITORIO_TOKEN", "")
    if reset and token:
        print("reset:", _llamar("POST", _base_http(url) + "/__reset", token))
    store = Store(":memory:")
    store.crear_tarea("local", caso["instruccion"], "api", None)
    cuadros = Cuadros(tempfile.mkdtemp(prefix="navegante-capturas-"))
    modelo = ClienteOpenRouter(
        os.environ["OPENROUTER_API_KEY"],
        costo_max=float(os.environ.get("COSTO_MAX_POR_TAREA", "0.50")),
    )
    inicio = time.monotonic()
    await ejecutar_tarea(
        task_id="local",
        instruccion=caso["instruccion"],
        url=url,
        password=SecretStr(os.environ["ESCRITORIO_PASSWORD"]),
        canal="api",
        store=store,
        cuadros=cuadros,
        api_key=os.environ["OPENROUTER_API_KEY"],
        costo_max=float(os.environ.get("COSTO_MAX_POR_TAREA", "0.50")),
        modelo=modelo,
    )
    final = store.obtener("local")
    print(f"\n--- {caso['id']}: {caso['instruccion']}")
    for e in store.eventos_desde("local"):
        if e["event"] in ("paso", "evidencia"):
            print(f"  [{e['event']}] {e['data'].get('texto', '')[:160]}")
    print(f"\nestado: {final['estado']} (esperado: {caso.get('estado_esperado', '?')})")
    print(f"resumen:\n{final['resumen']}")
    if "respuesta_esperada" in caso:
        print(f"respuesta esperada: {caso['respuesta_esperada']}")
    n_pasos = sum(1 for e in store.eventos_desde("local") if e["event"] == "paso")
    print(
        f"modelo: {modelo.modelo_id} | tiempo: {time.monotonic() - inicio:.0f} s | "
        f"costo: US$ {modelo.costo_acumulado:.4f} | pasos: {n_pasos}"
    )
    if token and caso["id"] != "libre":
        print("check:", _llamar("POST", _base_http(url) + "/__check", token, caso))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("Uso: python -m app.agente E5 [--sin-reset] [carpeta_pruebas]")
    carpeta = Path(args[1]) if len(args) > 1 else PRUEBAS
    asyncio.run(main(args[0], "--sin-reset" not in sys.argv, carpeta))
