import asyncio
import json
from contextlib import asynccontextmanager

from app.agente.falso import ModeloFalso
from app.agente.herramientas import (
    HERRAMIENTAS,
    Contexto,
    ResultadoHerramienta,
    ejecutar,
    esquemas_para_modelo,
)
from app.criterio.contrato import ContratoCambios
from app.rfb import ClienteRFB, ConexionPerdida
from tests.rfb.servidor_falso import PASSWORD_FALSA, ServidorFalso, levantar

CTRL = 0xFFE3


def correr(escenario):
    return asyncio.run(asyncio.wait_for(escenario(), 60))


@asynccontextmanager
async def entorno(respuestas, contrato=None, **kw):
    srv = ServidorFalso()
    modelo = ModeloFalso(respuestas)
    async with levantar(srv) as url, ClienteRFB(url, PASSWORD_FALSA, espera=0) as cliente:
        ctx = Contexto(
            cliente=cliente,
            modelo=modelo,
            contrato=contrato or ContratoCambios(),
            pausa_repintado=0,
            **kw,
        )
        yield ctx, srv, modelo


def punto(x, y):
    return {"encontrado": True, "x": x, "y": y, "motivo": ""}


def tabla(*filas, siguiente=None):
    return {"filas": list(filas), "siguiente": siguiente}


def tipos(srv):
    return [e[0] for e in srv.eventos]


def test_ver_devuelve_png_sin_tocar_el_modelo():
    async def escenario():
        async with entorno([]) as (ctx, srv, modelo):
            r = await ejecutar(ctx, "ver", {})
            assert r.ok and r.captura.startswith(b"\x89PNG")
            assert modelo.llamadas == [] and srv.eventos == []

    correr(escenario)


def test_ver_con_espero_pregunta_al_modelo_con_la_captura():
    async def escenario():
        resp = {"coincide": False, "descripcion": "Se ve el menú cerrado"}
        async with entorno([resp]) as (ctx, _, modelo):
            r = await ejecutar(ctx, "ver", {"espero": "submenú Maestros abierto"})
            assert not r.ok and "menú cerrado" in r.observacion
            assert modelo.llamadas[0]["imagen_png"].startswith(b"\x89PNG")
            assert "submenú Maestros abierto" in modelo.llamadas[0]["usuario"]

    correr(escenario)


def test_clic_usa_las_coordenadas_que_da_el_modelo():
    async def escenario():
        async with entorno([punto(321, 123)]) as (ctx, srv, _):
            r = await ejecutar(ctx, "clic", {"descripcion": "botón Buscar"})
            assert r.ok and r.captura
            assert ("puntero_abajo", 321, 123) in [e[:3] for e in srv.eventos]

    correr(escenario)


def test_hover_solo_mueve_el_puntero():
    async def escenario():
        async with entorno([punto(50, 60)]) as (ctx, srv, _):
            r = await ejecutar(ctx, "hover", {"descripcion": "menú Comercial"})
            assert r.ok
            assert tipos(srv) == ["puntero"] and srv.eventos[0][1:3] == (50, 60)

    correr(escenario)


def test_clic_sin_elemento_visible_no_actua():
    async def escenario():
        resp = {"encontrado": False, "x": 0, "y": 0, "motivo": "no está"}
        async with entorno([resp]) as (ctx, srv, _):
            r = await ejecutar(ctx, "clic", {"descripcion": "botón fantasma"})
            assert not r.ok and "botón fantasma" in r.observacion
            assert srv.eventos == []

    correr(escenario)


def test_clic_con_coordenadas_fuera_de_pantalla_no_actua():
    async def escenario():
        async with entorno([punto(5000, 10)]) as (ctx, srv, _):
            r = await ejecutar(ctx, "clic", {"descripcion": "algo"})
            assert not r.ok and srv.eventos == []

    correr(escenario)


def test_tecla_y_tecla_invalida():
    async def escenario():
        async with entorno([]) as (ctx, srv, _):
            assert (await ejecutar(ctx, "tecla", {"nombre": "ctrl+a"})).ok
            assert CTRL in [e[1] for e in srv.eventos]
            r = await ejecutar(ctx, "tecla", {"nombre": "teclainexistente"})
            assert not r.ok

    correr(escenario)


def test_leer_tabla_recorre_todas_las_paginas():
    async def escenario():
        resp = [
            tabla({"nombre": "A"}, siguiente={"x": 900, "y": 700}),
            tabla({"nombre": "B"}, siguiente={"x": 900, "y": 700}),
            tabla({"nombre": "C"}),
        ]
        async with entorno(resp) as (ctx, srv, _):
            r = await ejecutar(ctx, "leer_tabla", {})
            assert r.ok and r.evidencia["paginas"] == 3
            assert [f["nombre"] for f in r.evidencia["filas"]] == ["A", "B", "C"]
            assert tipos(srv).count("puntero_abajo") == 2

    correr(escenario)


def test_leer_tabla_se_detiene_si_siguiente_no_cambia_la_pagina():
    async def escenario():
        pag = tabla({"nombre": "A"}, siguiente={"x": 900, "y": 700})
        async with entorno([pag, pag]) as (ctx, _, _):
            r = await ejecutar(ctx, "leer_tabla", {})
            assert r.ok and r.evidencia["filas"] == [{"nombre": "A"}]

    correr(escenario)


def test_leer_tabla_no_devuelve_lectura_parcial_si_pasa_el_tope():
    async def escenario():
        resp = [tabla({"n": str(i)}, siguiente={"x": 9, "y": 9}) for i in range(5)]
        async with entorno(resp, max_paginas=3) as (ctx, _, _):
            r = await ejecutar(ctx, "leer_tabla", {})
            assert not r.ok and "más de 3 páginas" in r.observacion

    correr(escenario)


def test_buscar_registro_prueba_con_y_sin_tilde_y_cuenta():
    async def escenario():
        contrato = ContratoCambios(
            registro_objetivo={"nombre": "José Pérez"}, verbos_permitidos=frozenset({"guardar"})
        )
        resp = [
            punto(100, 100),
            tabla({"nombre": "José Pérez", "nit": "1"}),
            punto(100, 100),
            tabla({"nombre": "José Pérez", "nit": "1"}, {"nombre": "Jose Perez", "nit": "2"}),
        ]
        async with entorno(resp, contrato) as (ctx, srv, _):
            r = await ejecutar(ctx, "buscar_registro", {"campo": "Nombre", "texto": "José Pérez"})
            assert r.ok
            assert r.evidencia["variantes"] == ["José Pérez", "Jose Perez"]
            assert len(r.evidencia["candidatos"]) == 2  # sin duplicar la fila repetida
            assert ctx.registros_coincidentes == 1
            assert "2 candidatos" in r.observacion
            assert 0xFF08 in [e[1] for e in srv.eventos]  # vació el campo antes de teclear

    correr(escenario)


def test_buscar_registro_homonimos_deja_dos_coincidentes():
    async def escenario():
        contrato = ContratoCambios(
            registro_objetivo={"nombre": "Ana Torres"}, verbos_permitidos=frozenset({"guardar"})
        )
        filas = tabla({"nombre": "Ana Torres", "doc": "1"}, {"nombre": "Ana Torres", "doc": "2"})
        resp = [punto(1, 1), filas]  # sin tilde en el texto: una sola variante
        async with entorno(resp, contrato) as (ctx, _, _):
            r = await ejecutar(ctx, "buscar_registro", {"campo": "Nombre", "texto": "Ana Torres"})
            assert ctx.registros_coincidentes == 2
            assert "desempate" in r.evidencia

    correr(escenario)


def test_llenar_campos_selecciona_todo_teclea_y_relee():
    async def escenario():
        contrato = ContratoCambios(
            valores_permitidos={"Ciudad": ("Medellín",)}, verbos_permitidos=frozenset({"guardar"})
        )
        resp = [punto(200, 300), {"legible": True, "valor": "Medellín"}]
        async with entorno(resp, contrato) as (ctx, srv, _):
            r = await ejecutar(
                ctx, "llenar_campos", {"campos": [{"campo": "Ciudad", "valor": "Medellín"}]}
            )
            assert r.ok and r.evidencia["leidos"] == {"Ciudad": "Medellín"}
            teclas = [e[1] for e in srv.eventos if e[0] == "tecla_abajo"]
            assert (
                teclas[0] == 0xFF57
            )  # End, luego 80 BackSpace: el campo se vacía antes de teclear
            assert teclas[1:81] == [0xFF08] * 80
            assert len(teclas) == 1 + 80 + len("Medellín")

    correr(escenario)


def test_llenar_campos_detecta_que_el_valor_leido_no_coincide():
    async def escenario():
        contrato = ContratoCambios(
            valores_permitidos={"Ciudad": ("Cali",)}, verbos_permitidos=frozenset({"guardar"})
        )
        resp = [punto(1, 1), {"legible": True, "valor": "Cali Cali"}]
        async with entorno(resp, contrato) as (ctx, _, _):
            r = await ejecutar(
                ctx, "llenar_campos", {"campos": [{"campo": "Ciudad", "valor": "Cali"}]}
            )
            assert not r.ok and "Ciudad" in r.observacion

    correr(escenario)


def test_llenar_campos_rechaza_valor_fuera_del_contrato_sin_teclear():
    async def escenario():
        contrato = ContratoCambios(valores_permitidos={"Ciudad": ("Cali",)})
        async with entorno([], contrato) as (ctx, srv, modelo):
            r = await ejecutar(
                ctx, "llenar_campos", {"campos": [{"campo": "Ciudad", "valor": "Bogotá"}]}
            )
            assert not r.ok and r.fin == "fallida"
            assert "Bogotá" not in r.observacion  # el valor no se imprime
            assert modelo.llamadas == [] and srv.eventos == []

    correr(escenario)


def contrato_guardar():
    return ContratoCambios(verbos_permitidos=frozenset({"guardar"}))


def test_confirmar_registra_el_compromiso_antes_del_clic_y_una_sola_vez():
    async def escenario():
        async with entorno([punto(640, 700)], contrato_guardar()) as (ctx, srv, modelo):
            ctx.registros_coincidentes = 1
            visto = []
            clic_real = ctx.cliente.clic

            async def espia(x, y):
                visto.append(list(ctx.compromisos))
                await clic_real(x, y)

            ctx.cliente.clic = espia
            args = {"verbo": "guardar", "descripcion": "botón Guardar"}
            assert (await ejecutar(ctx, "confirmar", args)).ok
            assert visto == [["guardar"]]
            segundo = await ejecutar(ctx, "confirmar", args)
            assert not segundo.ok and "no se repite" in segundo.observacion
            assert tipos(srv).count("puntero_abajo") == 1
            assert len(modelo.llamadas) == 1

    correr(escenario)


def test_confirmar_no_reintenta_si_el_clic_falla():
    async def escenario():
        async with entorno([punto(640, 700)], contrato_guardar()) as (ctx, _, _):
            ctx.registros_coincidentes = 1

            async def roto(x, y):
                raise ConexionPerdida("se perdió la conexión con el escritorio")

            ctx.cliente.clic = roto
            args = {"verbo": "guardar", "descripcion": "botón Guardar"}
            r = await ejecutar(ctx, "confirmar", args)
            assert not r.ok and "No se sabe si" in r.observacion
            assert ctx.compromisos == ["guardar"]
            assert "no se repite" in (await ejecutar(ctx, "confirmar", args)).observacion

    correr(escenario)


def test_confirmar_exige_registro_verificado_y_verbo_permitido():
    async def escenario():
        async with entorno([], contrato_guardar()) as (ctx, srv, modelo):
            r = await ejecutar(ctx, "confirmar", {"verbo": "guardar", "descripcion": "Guardar"})
            assert not r.ok and r.fin == "fallida"  # registro sin verificar
            ctx.registros_coincidentes = 1
            r = await ejecutar(ctx, "confirmar", {"verbo": "eliminar", "descripcion": "Eliminar"})
            assert not r.ok and "no permite" in r.observacion
            assert ctx.compromisos == [] and srv.eventos == [] and modelo.llamadas == []

    correr(escenario)


def test_terminar_y_fallar_cierran_y_no_filtran_secretos():
    async def escenario():
        async with entorno([], secretos=(PASSWORD_FALSA,)) as (ctx, _, _):
            r = await ejecutar(
                ctx, "terminar", {"resumen": f"Listo {PASSWORD_FALSA}", "respuesta": "42"}
            )
            assert r.ok and r.fin == "terminada" and r.evidencia == {"respuesta": "42"}
            assert PASSWORD_FALSA not in r.observacion
            f = await ejecutar(ctx, "fallar", {"motivo": f"Dos Ana Torres {PASSWORD_FALSA}"})
            assert not f.ok and f.fin == "fallida" and PASSWORD_FALSA not in f.observacion

    correr(escenario)


def test_observaciones_y_evidencia_de_clic_no_filtran_secretos():
    async def escenario():
        async with entorno([punto(5, 5)], secretos=(PASSWORD_FALSA,)) as (ctx, _, _):
            r = await ejecutar(
                ctx, "clic", {"descripcion": "campo", "espero": f"nada {PASSWORD_FALSA}"}
            )
            assert PASSWORD_FALSA not in json.dumps(r.evidencia) + r.observacion

    correr(escenario)


def test_registro_y_validacion_de_argumentos():
    async def escenario():
        async with entorno([]) as (ctx, _, _):
            r = await ejecutar(ctx, "inventada", {})
            assert not r.ok
            r = await ejecutar(ctx, "clic", {})
            assert not r.ok and "faltan ['descripcion']" in r.observacion
            r = await ejecutar(ctx, "clic", {"descripcion": "x", "xy": [1, 2]})
            assert not r.ok and "sobran ['xy']" in r.observacion

    correr(escenario)
    assert set(HERRAMIENTAS) == {
        "ver", "clic", "hover", "tecla", "buscar_registro", "llenar_campos",
        "leer_tabla", "confirmar", "terminar", "fallar",
    }  # fmt: skip
    esquemas = json.loads(json.dumps(esquemas_para_modelo()))
    for e in esquemas:
        assert e["nombre"] and e["descripcion"] and e["argumentos"]["type"] == "object"
    assert isinstance(ResultadoHerramienta(ok=True, observacion=""), ResultadoHerramienta)
