"""Cliente RFB (VNC) sobre websocket: ojos (captura) y manos (mouse y teclado) del agente.

Solo habla lo mínimo: RFB 003.008, seguridad tipo 2 (VNC auth), codificación Raw y
formato de pixel de 32 bits. La contraseña vive en memoria y nunca aparece en
excepciones, `repr` ni logs; este módulo no registra nada.
"""

import asyncio
import struct
import time
import zlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Self

from pydantic import SecretStr
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException
from websockets.typing import Subprotocol

from app.rfb.des import respuesta_vnc
from app.rfb.teclas import keysym_de_caracter, keysyms_de_combinacion

ANCHO, ALTO = 1280, 800
ESPERA_TRAS_ACCION = 1.0  # la pantalla tarda hasta 1 s en repintar
PAUSA_CLIC = 0.12  # un clic de < 100 ms entre bajar y soltar se ignora
LIMITE_TAREA = 300.0  # 5 min por tarea
_MIN_PAUSA_CLIC = 0.1

_MSG_BELL, _MSG_SET_COLOURS, _MSG_CUT_TEXT, _MSG_UPDATE = 2, 1, 3, 0
_ENCODING_RAW = 0


class ErrorRFB(Exception):
    """Base de los errores del cliente. Los mensajes nunca llevan la contraseña."""


class ConexionPerdida(ErrorRFB):
    """El websocket se cayó o el escritorio no respondió."""


class AutenticacionRechazada(ErrorRFB):
    """El escritorio rechazó las credenciales."""


class ClienteCerrado(ErrorRFB):
    """Se intentó actuar después de `cerrar()`."""


class TiempoAgotado(ErrorRFB):
    """Pasaron los 5 min de la tarea; el cliente se cerró solo."""


@dataclass(frozen=True)
class Imagen:
    """Captura de pantalla. `sin_cambio` es True si es idéntica a la captura anterior."""

    ancho: int
    alto: int
    rgb: bytes
    sin_cambio: bool = False

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        i = (y * self.ancho + x) * 3
        return self.rgb[i], self.rgb[i + 1], self.rgb[i + 2]

    def a_png(self) -> bytes:
        """PNG sin dependencias externas (zlib estándar)."""

        def trozo(tipo: bytes, datos: bytes) -> bytes:
            cuerpo = tipo + datos
            return struct.pack(">I", len(datos)) + cuerpo + struct.pack(">I", zlib.crc32(cuerpo))

        paso = self.ancho * 3
        filas = b"".join(b"\x00" + self.rgb[y * paso : (y + 1) * paso] for y in range(self.alto))
        cabecera = struct.pack(">IIBBBBB", self.ancho, self.alto, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + trozo(b"IHDR", cabecera)
            + trozo(b"IDAT", zlib.compress(filas, 6))
            + trozo(b"IEND", b"")
        )

    def a_jpeg(self, calidad: int = 60) -> bytes:
        """JPEG para `pantalla.jpg`. Necesita Pillow, que aún no es dependencia del back."""
        try:
            from PIL import Image
        except ImportError as exc:
            raise ErrorRFB("falta la dependencia Pillow para generar JPEG") from exc
        import io

        salida = io.BytesIO()
        Image.frombytes("RGB", (self.ancho, self.alto), self.rgb).save(
            salida, format="JPEG", quality=calidad
        )
        return salida.getvalue()


class ClienteRFB:
    """Una sesión RFB. Las operaciones se serializan: de a una por vez.

    Tras una caída hace un solo intento de reconexión. Una captura se repite; una
    acción de mouse o teclado NO se repite (podría duplicar un clic): el llamador
    lo nota por `reconexiones` y verifica con una captura.
    """

    def __init__(
        self,
        url: str,
        password: SecretStr | str,
        *,
        espera: float = ESPERA_TRAS_ACCION,
        pausa_clic: float = PAUSA_CLIC,
        pausa_tecla: float = 0.02,
        limite: float = LIMITE_TAREA,
        timeout_red: float = 15.0,
    ) -> None:
        if pausa_clic <= _MIN_PAUSA_CLIC:
            raise ValueError("pausa_clic debe ser mayor a 0.1 s o el escritorio ignora el clic")
        self._url = url
        self._password = password if isinstance(password, SecretStr) else SecretStr(password)
        self._espera = espera
        self._pausa_clic = pausa_clic
        self._pausa_tecla = pausa_tecla
        self._limite = limite
        self._timeout_red = timeout_red
        self._ws: ClientConnection | None = None
        self._buf = bytearray()
        self._lock = asyncio.Lock()
        self._cerrado = False
        self._vence: float | None = None
        self._fb = bytearray()
        self._previo: bytes | None = None
        self._ultimo: Imagen | None = None
        self._jpeg: bytes | None = None
        self.ancho = ANCHO
        self.alto = ALTO
        self.reconexiones = 0
        self.texto_del_servidor = ""  # último "cut text" recibido (para X2)

    def __repr__(self) -> str:
        return f"ClienteRFB(cerrado={self._cerrado})"  # sin URL: puede traer un token

    async def __aenter__(self) -> Self:
        await self.conectar()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.cerrar()

    # --- ciclo de vida ---

    async def conectar(self) -> None:
        if self._cerrado:
            raise ClienteCerrado("el cliente ya se cerró")
        await self._abrir()
        self._vence = time.monotonic() + self._limite

    async def cerrar(self) -> None:
        """Idempotente. Después de esto no se vuelve a actuar."""
        self._cerrado = True
        ws, self._ws = self._ws, None
        if ws is not None:
            await ws.close()

    @property
    def ultimo_cuadro(self) -> Imagen | None:
        return self._ultimo

    def ultimo_cuadro_jpeg(self, calidad: int = 60) -> bytes | None:
        """JPEG de la última captura (lo que sirve `pantalla.jpg`), o None si no hay."""
        if self._ultimo is None:
            return None
        if self._jpeg is None:
            self._jpeg = self._ultimo.a_jpeg(calidad)
        return self._jpeg

    # --- acciones ---

    async def capturar(self) -> Imagen:
        imagen = await self._ejecutar(self._capturar, repetible=True)
        if imagen is None:
            raise ErrorRFB("la captura no devolvió imagen")
        return imagen

    async def mover(self, x: int, y: int) -> None:
        self._validar(x, y)
        await self._ejecutar(lambda: self._puntero(x, y, 0), repetible=False)
        await asyncio.sleep(self._espera)

    async def hover(self, x: int, y: int) -> None:
        """Pasa el mouse y espera: los submenús de SIGECOM abren así."""
        await self.mover(x, y)

    async def clic(self, x: int, y: int) -> None:
        self._validar(x, y)
        await self._ejecutar(lambda: self._clic(x, y), repetible=False)
        await asyncio.sleep(self._espera)

    async def doble_clic(self, x: int, y: int) -> None:
        self._validar(x, y)

        async def doble() -> None:
            await self._clic(x, y)
            await asyncio.sleep(self._pausa_clic)
            await self._clic(x, y)

        await self._ejecutar(doble, repetible=False)
        await asyncio.sleep(self._espera)

    async def teclear(self, texto: str) -> None:
        """Escribe texto. Si el campo ya tiene texto, el llamador hace `tecla("ctrl+a")` antes."""
        simbolos = [keysym_de_caracter(c) for c in texto]  # falla antes de enviar nada

        async def escribir() -> None:
            for s in simbolos:
                await self._tecla(s, True)
                await self._tecla(s, False)
                await asyncio.sleep(self._pausa_tecla)

        await self._ejecutar(escribir, repetible=False)
        await asyncio.sleep(self._espera)

    async def tecla(self, nombre: str) -> None:
        """Una tecla o combinación: `"enter"`, `"tab"`, `"ctrl+a"`, `"ctrl+c"`."""
        simbolos = keysyms_de_combinacion(nombre)

        pausa = max(self._pausa_tecla, 0.05)  # el servidor pierde combinaciones demasiado juntas

        async def pulsar() -> None:
            for s in simbolos:
                await self._tecla(s, True)
                await asyncio.sleep(pausa)
            for s in reversed(simbolos):
                await self._tecla(s, False)
                await asyncio.sleep(pausa)

        await self._ejecutar(pulsar, repetible=False)
        await asyncio.sleep(self._espera)

    async def borrar_campo(self, cuantos: int = 80) -> None:
        """Vacía el campo con foco sin usar modificadores: End y `cuantos` BackSpace.

        `ctrl+a` no seleccionó el texto en el navegador remoto y lo nuevo se concatenó
        a lo viejo ("Ferretería RuFeFerretería Ruiz"), así que no se depende de él."""
        fin = keysyms_de_combinacion("end")[0]
        borrar = keysyms_de_combinacion("backspace")[0]

        async def vaciar() -> None:
            for s in (fin, *([borrar] * cuantos)):
                await self._tecla(s, True)
                await self._tecla(s, False)
                await asyncio.sleep(self._pausa_tecla)

        await self._ejecutar(vaciar, repetible=False)
        await asyncio.sleep(self._espera)

    # --- núcleo ---

    def _validar(self, x: int, y: int) -> None:
        if not (0 <= x < self.ancho and 0 <= y < self.alto):
            raise ValueError(f"coordenada fuera de la pantalla: ({x}, {y})")

    async def _ejecutar[T](self, op: Callable[[], Awaitable[T]], *, repetible: bool) -> T | None:
        async with self._lock:
            await self._verificar_vivo()
            try:
                return await op()
            except ConexionPerdida:
                await self._reconectar()
                if repetible:
                    return await op()
                return None

    async def _verificar_vivo(self) -> None:
        if self._cerrado:
            raise ClienteCerrado("el cliente ya se cerró")
        if self._ws is None:
            raise ErrorRFB("el cliente no está conectado")
        if self._vence is not None and time.monotonic() > self._vence:
            await self.cerrar()
            raise TiempoAgotado("se acabó el tiempo de la tarea")

    async def _reconectar(self) -> None:
        try:
            await self._abrir()
        except AutenticacionRechazada:
            raise
        except ErrorRFB:
            raise ConexionPerdida("se perdió la conexión con el escritorio") from None
        self.reconexiones += 1

    async def _abrir(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._buf.clear()
        try:
            ws = await connect(
                self._url,
                subprotocols=[Subprotocol("binary")],
                max_size=None,
                open_timeout=self._timeout_red,
            )
        except (OSError, WebSocketException, TimeoutError) as exc:
            raise ConexionPerdida(
                f"no se pudo abrir el websocket del escritorio ({type(exc).__name__})"
            ) from None
        self._ws = ws
        try:
            if ws.subprotocol != "binary":
                raise ErrorRFB("el escritorio no aceptó el subprotocolo binary")
            await self._handshake()
        except BaseException:
            self._ws = None
            await ws.close()
            raise

    async def _handshake(self) -> None:
        version = await self._leer(12)
        if not version.startswith(b"RFB 003.") or int(version[8:11]) < 8:
            raise ErrorRFB("versión de RFB no soportada (se pide 003.008)")
        await self._enviar(b"RFB 003.008\n")

        n = (await self._leer(1))[0]
        if n == 0:
            raise ErrorRFB("el escritorio rechazó la conexión")
        tipos = await self._leer(n)
        if 2 not in tipos:
            raise ErrorRFB("el escritorio no ofrece VNC auth (tipo 2)")
        await self._enviar(b"\x02")
        desafio = await self._leer(16)
        await self._enviar(respuesta_vnc(self._password.get_secret_value(), desafio))
        (resultado,) = struct.unpack(">I", await self._leer(4))
        if resultado != 0:
            (largo,) = struct.unpack(">I", await self._leer(4))
            await self._leer(min(largo, 4096))  # el motivo del servidor no se propaga
            raise AutenticacionRechazada("el escritorio rechazó la autenticación")

        await self._enviar(b"\x01")  # ClientInit: pantalla compartida
        ancho, alto = struct.unpack(">HH", await self._leer(4))
        await self._leer(16)  # formato de pixel del servidor; se reemplaza abajo
        (largo_nombre,) = struct.unpack(">I", await self._leer(4))
        await self._leer(min(largo_nombre, 4096))
        self.ancho, self.alto = ancho, alto
        self._fb = bytearray(ancho * alto * 4)

        # 32 bpp, profundidad 24, little-endian, true colour, R<<16 G<<8 B -> bytes B,G,R,X
        formato = struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        await self._enviar(b"\x00\x00\x00\x00" + formato)
        await self._enviar(struct.pack(">BxHi", 2, 1, _ENCODING_RAW))

    async def _capturar(self) -> Imagen:
        await self._enviar(struct.pack(">BBHHHH", 3, 0, 0, 0, self.ancho, self.alto))
        while True:
            tipo = (await self._leer(1))[0]
            if tipo == _MSG_UPDATE:
                await self._leer_actualizacion()
                break
            await self._descartar_mensaje(tipo)
        rgb = bytearray(self.ancho * self.alto * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = self._fb[2::4], self._fb[1::4], self._fb[0::4]
        actual = bytes(rgb)
        imagen = Imagen(self.ancho, self.alto, actual, sin_cambio=actual == self._previo)
        self._previo, self._ultimo, self._jpeg = actual, imagen, None
        return imagen

    async def _leer_actualizacion(self) -> None:
        (n,) = struct.unpack(">xH", await self._leer(3))
        for _ in range(n):
            x, y, w, h, codificacion = struct.unpack(">HHHHi", await self._leer(12))
            if codificacion != _ENCODING_RAW:
                raise ErrorRFB(f"codificación no soportada: {codificacion}")
            if x + w > self.ancho or y + h > self.alto:
                raise ErrorRFB("el escritorio mandó un rectángulo fuera de la pantalla")
            datos = await self._leer(w * h * 4)
            for fila in range(h):
                inicio = ((y + fila) * self.ancho + x) * 4
                self._fb[inicio : inicio + w * 4] = datos[fila * w * 4 : (fila + 1) * w * 4]

    async def _descartar_mensaje(self, tipo: int) -> None:
        if tipo == _MSG_BELL:
            return
        if tipo == _MSG_SET_COLOURS:
            _, n = struct.unpack(">xHH", await self._leer(5))
            await self._leer(n * 6)
        elif tipo == _MSG_CUT_TEXT:
            (largo,) = struct.unpack(">xxxI", await self._leer(7))
            texto = await self._leer(largo)
            self.texto_del_servidor = texto.decode("latin-1")
        else:
            raise ErrorRFB(f"mensaje del servidor desconocido: {tipo}")

    async def _puntero(self, x: int, y: int, mascara: int) -> None:
        await self._enviar(struct.pack(">BBHH", 5, mascara, x, y))

    async def _clic(self, x: int, y: int) -> None:
        await self._puntero(x, y, 0)
        await asyncio.sleep(0.05)
        await self._puntero(x, y, 1)
        await asyncio.sleep(self._pausa_clic)
        await self._puntero(x, y, 0)

    async def _tecla(self, keysym: int, abajo: bool) -> None:
        await self._enviar(struct.pack(">BBxxI", 4, int(abajo), keysym))

    # --- red ---

    async def _enviar(self, datos: bytes) -> None:
        if self._ws is None:
            raise ConexionPerdida("se perdió la conexión con el escritorio")
        try:
            await self._ws.send(datos)
        except (WebSocketException, OSError):
            raise ConexionPerdida("se perdió la conexión con el escritorio") from None

    async def _leer(self, n: int) -> bytes:
        while len(self._buf) < n:
            if self._ws is None:
                raise ConexionPerdida("se perdió la conexión con el escritorio")
            try:
                mensaje = await asyncio.wait_for(self._ws.recv(), self._timeout_red)
            except (WebSocketException, OSError):
                raise ConexionPerdida("se perdió la conexión con el escritorio") from None
            except TimeoutError:
                raise ConexionPerdida("el escritorio no respondió a tiempo") from None
            if isinstance(mensaje, str):
                raise ErrorRFB("el escritorio mandó texto por el canal binario")
            self._buf += mensaje
        datos = bytes(self._buf[:n])
        del self._buf[:n]
        return datos
