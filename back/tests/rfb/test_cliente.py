import asyncio
import traceback

import pytest

from app.rfb import (
    AutenticacionRechazada,
    ClienteCerrado,
    ClienteRFB,
    ConexionPerdida,
    ErrorRFB,
    TiempoAgotado,
)
from app.rfb.des import cifrar_bloque, respuesta_vnc
from tests.rfb.servidor_falso import ALTO, ANCHO, PASSWORD_FALSA, ServidorFalso, levantar


def correr(escenario):
    return asyncio.run(asyncio.wait_for(escenario(), 60))


def cliente(url: str, password: str = PASSWORD_FALSA, **kw) -> ClienteRFB:
    kw.setdefault("espera", 0)
    return ClienteRFB(url, password, **kw)


def test_des_vector_estandar():
    esperado = cifrar_bloque(bytes.fromhex("133457799BBCDFF1"), bytes.fromhex("0123456789ABCDEF"))
    assert esperado.hex() == "85e813540f0ab405"


def test_respuesta_vnc_vector_independiente():
    # Calculado aparte con `openssl enc -des-ecb` y la clave con bits invertidos.
    r = respuesta_vnc(PASSWORD_FALSA, bytes(range(16)))
    assert r.hex() == "02f5048f3c3ad2bd641c4bb08cdc6f94"


def test_conecta_y_captura_1280x800():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            img = await c.capturar()
            assert (img.ancho, img.alto) == (ANCHO, ALTO) == (1280, 800)
            assert len(img.rgb) == 1280 * 800 * 3
            for x, y in [(0, 0), (1279, 799), (300, 650), (640, 399), (5, 400)]:
                assert img.pixel(x, y) == srv.pixel(x, y)  # une las dos mitades bien
            assert img.a_png().startswith(b"\x89PNG")
            assert c.ultimo_cuadro is img

    correr(escenario)
    assert srv.codificaciones == [0]
    assert srv.formato is not None and srv.formato[:4] == bytes([32, 24, 0, 1])


def test_ignora_bell_y_cut_text_antes_de_la_actualizacion():
    srv = ServidorFalso()
    srv.con_ruido = True

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.capturar()
            assert c.texto_del_servidor == "portapapeles falso"

    correr(escenario)


def test_sin_cambio_se_reporta():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            assert (await c.capturar()).sin_cambio is False
            assert (await c.capturar()).sin_cambio is True
            await c.clic(10, 10)  # el servidor falso cambia de tono al recibir clic
            assert (await c.capturar()).sin_cambio is False

    correr(escenario)


def test_clic_mantiene_mas_de_100ms():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.clic(200, 300)
            await c.doble_clic(400, 500)

    correr(escenario)
    bajadas = [e for e in srv.eventos if e[0] == "puntero_abajo"]
    assert [(e[1], e[2]) for e in bajadas] == [(200, 300), (400, 500), (400, 500)]
    # cada "abajo" va seguido de un "arriba" (puntero con máscara 0) tras > 100 ms
    for i, e in enumerate(srv.eventos):
        if e[0] == "puntero_abajo":
            siguiente = srv.eventos[i + 1]
            assert siguiente[0] == "puntero"
            assert siguiente[3] - e[3] > 0.1


def test_pausa_de_clic_menor_a_100ms_se_rechaza():
    with pytest.raises(ValueError):
        ClienteRFB("ws://x", "p", pausa_clic=0.05)


def test_espera_tras_accion():
    srv = ServidorFalso()

    async def escenario():
        loop = asyncio.get_running_loop()
        async with levantar(srv) as url, cliente(url, espera=0.4) as c:
            t0 = loop.time()
            await c.hover(100, 100)
            assert loop.time() - t0 >= 0.4

    correr(escenario)
    assert ("puntero", 100, 100) == srv.eventos[-1][:3]


def test_teclear_tildes_y_tecla_combinada():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.tecla("ctrl+a")
            await c.teclear("Año\n€")
            await c.tecla("F5")

    correr(escenario)
    pulsaciones = [(e[0], e[1]) for e in srv.eventos]
    assert pulsaciones[:4] == [
        ("tecla_abajo", 0xFFE3),
        ("tecla_abajo", ord("a")),
        ("tecla_arriba", ord("a")),
        ("tecla_arriba", 0xFFE3),
    ]
    bajadas = [k for tipo, k in pulsaciones[4:] if tipo == "tecla_abajo"]
    assert bajadas == [ord("A"), 0xF1, ord("o"), 0xFF0D, 0x010020AC, 0xFFC2]


def test_teclas_invalidas_no_envian_nada():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            with pytest.raises(ValueError):
                await c.tecla("ctrl+nada")
            with pytest.raises(ValueError):
                await c.teclear("ok\x07")
            with pytest.raises(ValueError):
                await c.clic(1280, 0)

    correr(escenario)
    assert srv.eventos == []


def test_autenticacion_rechazada_no_expone_la_contrasena():
    srv = ServidorFalso()
    mala = "otra-clave-77"

    async def escenario():
        async with levantar(srv) as url:
            c = cliente(url, mala)
            with pytest.raises(AutenticacionRechazada) as info:
                await c.conectar()
            texto = "".join(traceback.format_exception(info.value))
            assert mala not in texto and PASSWORD_FALSA not in texto
            assert mala not in repr(c) and mala not in str(c)

    correr(escenario)


def test_contrasena_no_aparece_en_logs(caplog):
    srv = ServidorFalso()
    caplog.set_level("DEBUG")

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.capturar()

    correr(escenario)
    assert PASSWORD_FALSA not in caplog.text


def test_seguridad_sin_tipo_2_falla_claro():
    srv = ServidorFalso()
    srv.tipos_seguridad = b"\x01"

    async def escenario():
        async with levantar(srv) as url:
            with pytest.raises(ErrorRFB, match="VNC auth"):
                await cliente(url).conectar()

    correr(escenario)


def test_caida_reconecta_una_vez_y_repite_la_captura():
    srv = ServidorFalso()
    srv.caer_conexion_1_tras = 3  # SetPixelFormat, SetEncodings y la primera petición

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            img = await c.capturar()
            assert img.pixel(7, 7) == srv.pixel(7, 7)
            assert c.reconexiones == 1

    correr(escenario)
    assert srv.conexiones == 2


def test_caida_en_accion_reconecta_sin_repetir_el_clic():
    srv = ServidorFalso()
    srv.caer_conexion_1_tras = 3  # cae al llegar el primer evento de puntero

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.clic(10, 10)
            assert c.reconexiones == 1

    correr(escenario)
    assert [e for e in srv.eventos if e[0] == "puntero_abajo"] == []


def test_si_la_reconexion_falla_dice_que_se_perdio_la_conexion():
    srv = ServidorFalso()
    srv.caer_conexion_1_tras = 3
    srv.cerrar_desde_conexion = 2

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            with pytest.raises(ConexionPerdida, match="se perdió la conexión con el escritorio"):
                await c.capturar()

    correr(escenario)


def test_no_conecta_a_un_puerto_cerrado():
    async def escenario():
        with pytest.raises(ConexionPerdida):
            await cliente("ws://127.0.0.1:1/websockify", timeout_red=2).conectar()

    correr(escenario)


def test_despues_de_cerrar_no_se_actua():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url:
            c = cliente(url)
            await c.conectar()
            await c.cerrar()
            await c.cerrar()  # idempotente
            for accion in (c.capturar, lambda: c.clic(1, 1), lambda: c.tecla("enter")):
                with pytest.raises(ClienteCerrado):
                    await accion()
            with pytest.raises(ClienteCerrado):
                await c.conectar()

    correr(escenario)
    assert srv.eventos == []


def test_a_los_5_minutos_se_cierra_solo():
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url:
            c = cliente(url, limite=0.2)
            await c.conectar()
            await c.capturar()
            await asyncio.sleep(0.3)
            with pytest.raises(TiempoAgotado):
                await c.clic(5, 5)
            with pytest.raises(ClienteCerrado):
                await c.capturar()

    correr(escenario)


def test_jpeg_con_pillow():
    pytest.importorskip("PIL")
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.capturar()
            assert c.ultimo_cuadro_jpeg()[:2] == b"\xff\xd8"

    correr(escenario)


def test_jpeg_sin_pillow_falla_explicito(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "PIL", None)
    srv = ServidorFalso()

    async def escenario():
        async with levantar(srv) as url, cliente(url) as c:
            await c.capturar()
            with pytest.raises(ErrorRFB, match="Pillow"):
                c.ultimo_cuadro_jpeg()

    correr(escenario)
