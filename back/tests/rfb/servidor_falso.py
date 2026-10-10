"""Servidor RFB falso para los tests: 003.008, VNC auth, subprotocolo binary, 1280x800."""

import asyncio
import os
import struct
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.typing import Subprotocol

from app.rfb.des import respuesta_vnc

PASSWORD_FALSA = "falsa-12"  # contraseña inventada para tests
ANCHO, ALTO = 1280, 800


class ServidorFalso:
    def __init__(self, *, password: str = PASSWORD_FALSA) -> None:
        self.password = password
        self.conexiones = 0
        self.eventos: list[tuple[str, int, int, float]] = []  # (tipo, a, b, instante)
        self.formato: bytes | None = None
        self.codificaciones: list[int] = []
        self.tono = 10
        self.caer_conexion_1_tras = 0  # cierra la conexión 1 tras N mensajes del cliente
        self.cerrar_desde_conexion = 0  # desde la conexión N, cierra apenas acepta
        self.con_ruido = False  # Bell + ServerCutText antes de cada actualización
        self.version = b"RFB 003.008\n"
        self.tipos_seguridad = b"\x02"

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        return x % 256, y % 256, self.tono

    def _filas(self, y0: int, y1: int) -> bytes:
        filas = bytearray()
        for y in range(y0, y1):
            fila = bytearray(ANCHO * 4)
            fila[0::4] = bytes([self.tono]) * ANCHO
            fila[1::4] = bytes([y % 256]) * ANCHO
            fila[2::4] = bytes(x % 256 for x in range(ANCHO))
            filas += fila
        return bytes(filas)

    async def _manejar(self, ws: ServerConnection) -> None:
        self.conexiones += 1
        numero = self.conexiones
        if self.cerrar_desde_conexion and numero >= self.cerrar_desde_conexion:
            await ws.close()
            return
        buf = bytearray()

        async def leer(n: int) -> bytes:
            while len(buf) < n:
                buf.extend(await ws.recv())
            datos = bytes(buf[:n])
            del buf[:n]
            return datos

        try:
            await self._handshake(ws, leer)
            mensajes = 0
            while True:
                tipo = (await leer(1))[0]
                mensajes += 1
                if (
                    numero == 1
                    and self.caer_conexion_1_tras
                    and mensajes >= self.caer_conexion_1_tras
                ):
                    await ws.close()
                    return
                await self._mensaje(ws, leer, tipo)
        except ConnectionClosed:
            return

    async def _handshake(self, ws, leer) -> None:
        await ws.send(self.version)
        assert await leer(12) == b"RFB 003.008\n"
        await ws.send(bytes([len(self.tipos_seguridad)]) + self.tipos_seguridad)
        if not self.tipos_seguridad:
            return
        assert await leer(1) == b"\x02"
        desafio = os.urandom(16)
        await ws.send(desafio)
        respuesta = await leer(16)
        if respuesta != respuesta_vnc(self.password, desafio):
            motivo = b"autenticacion fallida"
            await ws.send(struct.pack(">II", 1, len(motivo)) + motivo)
            await ws.close()
            raise ConnectionClosed(None, None)
        await ws.send(struct.pack(">I", 0))
        await leer(1)  # ClientInit
        nombre = b"escritorio-falso"
        formato = struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        await ws.send(
            struct.pack(">HH", ANCHO, ALTO) + formato + struct.pack(">I", len(nombre)) + nombre
        )

    async def _mensaje(self, ws, leer, tipo: int) -> None:
        ahora = time.monotonic()
        if tipo == 0:
            await leer(3)
            self.formato = await leer(16)
        elif tipo == 2:
            (n,) = struct.unpack(">xH", await leer(3))
            self.codificaciones = [struct.unpack(">i", await leer(4))[0] for _ in range(n)]
        elif tipo == 3:
            await leer(9)
            await self._actualizar(ws)
        elif tipo == 4:
            abajo, _, tecla = struct.unpack(">BHI", await leer(7))
            self.eventos.append(("tecla_abajo" if abajo else "tecla_arriba", tecla, 0, ahora))
        elif tipo == 5:
            mascara, x, y = struct.unpack(">BHH", await leer(5))
            nombre = "puntero_abajo" if mascara else "puntero"
            if mascara:
                self.tono = (self.tono + 37) % 256
            self.eventos.append((nombre, x, y, ahora))
        else:
            raise AssertionError(f"mensaje de cliente inesperado: {tipo}")

    async def _actualizar(self, ws) -> None:
        if self.con_ruido:
            texto = b"portapapeles falso"
            await ws.send(b"\x02")
            await ws.send(b"\x03\x00\x00\x00" + struct.pack(">I", len(texto)) + texto)
        mitad = ALTO // 2
        cuerpo = b"\x00\x00" + struct.pack(">H", 2)
        for y0, y1 in ((0, mitad), (mitad, ALTO)):
            cuerpo += struct.pack(">HHHHi", 0, y0, ANCHO, y1 - y0, 0) + self._filas(y0, y1)
        # Trozos de tamaño raro: el cliente no debe depender de cómo llegan los frames.
        for i in range(0, len(cuerpo), 65537):
            await ws.send(cuerpo[i : i + 65537])


@asynccontextmanager
async def levantar(servidor: ServidorFalso) -> AsyncIterator[str]:
    async with serve(
        servidor._manejar,
        "127.0.0.1",
        0,
        subprotocols=[Subprotocol("binary")],
        max_size=None,
    ) as s:
        puerto = s.sockets[0].getsockname()[1]
        yield f"ws://127.0.0.1:{puerto}/websockify"
        await asyncio.sleep(0)
