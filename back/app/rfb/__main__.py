"""Verificación X1 contra un escritorio real: captura, un clic, una tecla, captura.

    ESCRITORIO_URL=wss://.../websockify ESCRITORIO_PASSWORD=... \
        uv run python -m app.rfb X Y [salida_dir]

La contraseña se lee del entorno de tu terminal; el script nunca la imprime.
Elige un X Y inofensivo (por ejemplo, una zona vacía): el clic es real.
"""

import asyncio
import os
import sys
from pathlib import Path

from app.rfb.cliente import ClienteRFB


async def main(x: int, y: int, salida: Path) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    async with ClienteRFB(os.environ["ESCRITORIO_URL"], os.environ["ESCRITORIO_PASSWORD"]) as c:
        antes = await c.capturar()
        (salida / "antes.png").write_bytes(antes.a_png())
        await c.clic(x, y)
        await c.tecla("shift")
        despues = await c.capturar()
        (salida / "despues.png").write_bytes(despues.a_png())
        print(
            f"{despues.ancho}x{despues.alto}, sin_cambio={despues.sin_cambio}, guardado en {salida}"
        )


if __name__ == "__main__":
    asyncio.run(
        main(
            int(sys.argv[1]),
            int(sys.argv[2]),
            Path(sys.argv[3] if len(sys.argv) > 3 else "capturas"),
        )
    )
