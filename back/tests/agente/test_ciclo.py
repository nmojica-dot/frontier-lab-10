import asyncio
import json

from app.agente.ciclo import CIERRE, SIN_COMPROMISOS_DESDE, correr_ciclo
from app.agente.falso import ModeloFalso
from app.agente.herramientas import Contexto, ResultadoHerramienta
from app.criterio.contrato import ContratoCambios
from app.cuadros import Cuadros
from app.store import Store
from tests.conftest import PASSWORD_FALSA


def decision(herramienta: str, **args) -> dict:
    return {"herramienta": herramienta, "argumentos_json": json.dumps(args), "razon": "x"}


class Herramientas:
    """Ejecutor de mentira: devuelve resultados fijos por nombre y anota las llamadas."""

    def __init__(self, resultados: dict[str, ResultadoHerramienta]) -> None:
        self.resultados = resultados
        self.llamadas: list[str] = []

    async def __call__(self, ctx, nombre, args):
        self.llamadas.append(nombre)
        return self.resultados.get(nombre, ResultadoHerramienta(ok=True, observacion="ok"))


def armar(tmp_path, decisiones, resultados, contrato=None):
    store = Store(str(tmp_path / "t.db"))
    store.crear_tarea("t1", "tarea", "api", None)
    ctx = Contexto(
        cliente=None,  # type: ignore[arg-type]
        modelo=ModeloFalso(decisiones),
        contrato=contrato or ContratoCambios(pregunta="¿cuántas facturas vencidas?"),
        secretos=(PASSWORD_FALSA,),
    )
    return ctx, store, Cuadros(str(tmp_path / "capturas")), Herramientas(resultados)


def correr(ctx, store, cuadros, herr, **kw):
    return asyncio.run(
        correr_ciclo(
            ctx,
            instruccion="¿cuántas facturas vencidas tiene Ana?",
            task_id="t1",
            store=store,
            cuadros=cuadros,
            ejecutar_herramienta=herr,
            **kw,
        )
    )


LEER = ResultadoHerramienta(ok=True, observacion="Leí 3 filas", evidencia={"filas": 3})
TERMINAR = ResultadoHerramienta(
    ok=True, observacion="Tiene 3 vencidas", evidencia={"respuesta": "3"}, fin="terminada"
)
FALLAR = ResultadoHerramienta(ok=False, observacion="no pude", fin="fallida")


def test_consulta_con_evidencia_termina_con_respuesta(tmp_path):
    ctx, store, cuadros, herr = armar(
        tmp_path,
        [decision("leer_tabla"), decision("terminar", resumen="x", respuesta="3")],
        {"leer_tabla": LEER, "terminar": TERMINAR},
    )
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "terminada"
    assert "respuesta: 3" in resumen
    eventos = [e["event"] for e in store.eventos_desde("t1")]
    assert eventos.count("paso") == 2 and "evidencia" in eventos


def test_terminar_sin_evidencia_es_fallida(tmp_path):
    ctx, store, cuadros, herr = armar(
        tmp_path, [decision("terminar", resumen="x", respuesta="3")], {"terminar": TERMINAR}
    )
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida"
    assert "evidencia" in resumen


def test_fallar_deja_el_motivo_con_los_datos(tmp_path):
    fallo = ResultadoHerramienta(
        ok=False, observacion="Dos Ana Torres: 52345678 y 1019876543", fin="fallida"
    )
    ctx, store, cuadros, herr = armar(tmp_path, [decision("fallar", motivo="x")], {"fallar": fallo})
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida"
    assert "52345678" in resumen and "1019876543" in resumen


def test_la_contrasena_se_redacta_en_pasos_y_resumen(tmp_path):
    filtra = ResultadoHerramienta(
        ok=False, observacion=f"La pantalla mostraba {PASSWORD_FALSA}", fin="fallida"
    )
    ctx, store, cuadros, herr = armar(
        tmp_path, [decision("fallar", motivo="x")], {"fallar": filtra}
    )
    _, resumen = correr(ctx, store, cuadros, herr)
    assert PASSWORD_FALSA not in resumen
    assert PASSWORD_FALSA not in str(store.eventos_desde("t1"))


def test_confirmar_desde_3_45_no_se_ejecuta(tmp_path):
    ctx, store, cuadros, herr = armar(
        tmp_path,
        [decision("confirmar", verbo="guardar", descripcion="boton")],
        {},
        contrato=ContratoCambios(verbos_permitidos=frozenset({"guardar"})),
    )
    tiempos = iter([0.0, 0.0, SIN_COMPROMISOS_DESDE + 1, SIN_COMPROMISOS_DESDE + 1])
    estado, resumen = correr(ctx, store, cuadros, herr, reloj=lambda: next(tiempos))
    assert estado == "fallida"
    assert "confirmar" not in herr.llamadas
    assert "3:45" in resumen


def test_se_acaba_el_tiempo(tmp_path):
    ctx, store, cuadros, herr = armar(tmp_path, [decision("ver")], {})
    tiempos = iter([0.0, CIERRE + 1])
    estado, resumen = correr(ctx, store, cuadros, herr, reloj=lambda: next(tiempos))
    assert estado == "fallida" and "tiempo" in resumen


def test_respuesta_con_mas_de_dos_datos_es_fallida(tmp_path):
    triple = ResultadoHerramienta(
        ok=True, observacion="x", evidencia={"respuesta": "1; 2; 3"}, fin="terminada"
    )
    ctx, store, cuadros, herr = armar(
        tmp_path,
        [decision("leer_tabla"), decision("terminar", resumen="x")],
        {"leer_tabla": LEER, "terminar": triple},
    )
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida" and "Formato de respuesta" in resumen


def test_el_modelo_que_falla_seguido_cierra_fallida(tmp_path):
    ctx, store, cuadros, herr = armar(tmp_path, [], {})  # ModeloFalso sin respuestas
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida" and "modelo" in resumen
    assert set(herr.llamadas) == {"ver"}  # solo observó; nunca actuó


def test_argumentos_que_no_son_json_no_ejecutan_nada(tmp_path):
    malo = {"herramienta": "clic", "argumentos_json": "no es json", "razon": "x"}
    ctx, store, cuadros, herr = armar(tmp_path, [malo, malo, malo], {})
    estado, _ = correr(ctx, store, cuadros, herr)
    assert estado == "fallida"
    assert "clic" not in herr.llamadas


def test_un_compromiso_sin_verificar_queda_en_el_resumen(tmp_path):
    incierto = ResultadoHerramienta(
        ok=False, observacion="No se sabe si «guardar» se ejecutó", evidencia={"ejecutado": None}
    )
    ctx, store, cuadros, herr = armar(
        tmp_path,
        [decision("confirmar", verbo="guardar", descripcion="b"), decision("fallar", motivo="x")],
        {"confirmar": incierto, "fallar": FALLAR},
        contrato=ContratoCambios(verbos_permitidos=frozenset({"guardar"})),
    )
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida"
    assert "No se sabe si" in resumen


def test_terminar_tras_guardar_sin_mirar_pide_verificar_una_vez(tmp_path):
    class Guardando(Herramientas):
        async def __call__(self, ctx, nombre, args):
            if nombre == "confirmar":
                ctx.compromisos.append("guardar")
            return await super().__call__(ctx, nombre, args)

    ctx, store, cuadros, _ = armar(
        tmp_path,
        [
            decision("confirmar", verbo="guardar", descripcion="b"),
            decision("terminar", resumen="listo"),
            decision("ver", espero="Cambios aplicados"),
            decision("terminar", resumen="listo"),
        ],
        {},
        contrato=ContratoCambios(verbos_permitidos=frozenset({"guardar"})),
    )
    herr = Guardando({"terminar": ResultadoHerramienta(ok=True, observacion="ok", fin="terminada")})
    estado, _ = correr(ctx, store, cuadros, herr)
    assert estado == "terminada"
    assert herr.llamadas.count("terminar") == 2 and "ver" in herr.llamadas


def test_sin_cerrar_nunca_pasa_de_25_decisiones(tmp_path):
    ctx, store, cuadros, herr = armar(tmp_path, [decision("ver")] * 40, {})
    estado, resumen = correr(ctx, store, cuadros, herr)
    assert estado == "fallida" and "25 decisiones" in resumen
