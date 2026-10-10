import asyncio
import base64
import json

import httpx
import pytest

from app.agente.falso import ModeloFalso
from app.agente.openrouter import ClienteOpenRouter
from app.agente.tipos import ErrorModelo, TopeDeCosto

LLAVE = "llave-falsa-OR-4Z8K"
ESQUEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}


def ok(contenido: str = '{"ok": true}', costo: float | None = 0.01) -> httpx.Response:
    usage: dict = {"prompt_tokens": 10, "completion_tokens": 5}
    if costo is not None:
        usage["cost"] = costo
    cuerpo = {"choices": [{"message": {"content": contenido}}], "usage": usage}
    return httpx.Response(200, json=cuerpo)


def montar(*respuestas, **kw):
    """Devuelve (cliente, peticiones). Cada petición usa la siguiente respuesta (o excepción)."""
    peticiones: list[httpx.Request] = []
    cola = list(respuestas)

    def manejar(req: httpx.Request) -> httpx.Response:
        peticiones.append(req)
        r = cola.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    cliente = ClienteOpenRouter(LLAVE, transport=httpx.MockTransport(manejar), **kw)
    return cliente, peticiones


def pedir(cliente, **kw):
    return asyncio.run(cliente.pedir_json(sistema="s", usuario="u", esquema=ESQUEMA, **kw))


def test_camino_feliz_y_cuerpo_de_la_peticion():
    cliente, reqs = montar(ok(), modelo_id="x/y", proveedores=["prov"])
    png = b"\x89PNGfalso"
    r = pedir(cliente, imagen_png=png)
    assert r.datos == {"ok": True}
    assert r.costo == 0.01 and r.tokens_entrada == 10 and r.tokens_salida == 5
    assert reqs[0].headers["authorization"] == f"Bearer {LLAVE}"
    cuerpo = json.loads(reqs[0].content)
    assert cuerpo["model"] == "x/y"
    assert cuerpo["usage"] == {"include": True}
    assert cuerpo["provider"] == {"order": ["prov"], "allow_fallbacks": False}
    rf = cuerpo["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is False
    assert rf["json_schema"]["schema"] == ESQUEMA
    partes = cuerpo["messages"][1]["content"]
    assert (
        partes[1]["image_url"]["url"] == "data:image/png;base64," + base64.b64encode(png).decode()
    )


def test_sin_imagen_ni_proveedor():
    cliente, reqs = montar(ok())
    pedir(cliente)
    cuerpo = json.loads(reqs[0].content)
    assert "provider" not in cuerpo
    assert [p["type"] for p in cuerpo["messages"][1]["content"]] == ["text"]


def test_modelo_desde_entorno(monkeypatch):
    monkeypatch.setenv("MODELO_ID", "env/modelo")
    cliente, reqs = montar(ok())
    pedir(cliente)
    assert json.loads(reqs[0].content)["model"] == "env/modelo"


def test_costo_se_acumula_y_corta_al_pasarse():
    cliente, reqs = montar(ok(costo=0.03), ok(costo=0.03), ok(), costo_max=0.05)
    pedir(cliente)
    with pytest.raises(TopeDeCosto):
        pedir(cliente)  # 0.06 > 0.05, tras la llamada
    assert len(reqs) == 2
    with pytest.raises(TopeDeCosto):
        pedir(cliente)  # ya pasado: ni siquiera llama
    assert len(reqs) == 2


def test_reintenta_una_vez_ante_red_y_5xx():
    cliente, reqs = montar(httpx.ConnectError("boom"), httpx.Response(503), ok())
    with pytest.raises(ErrorModelo):
        pedir(cliente)
    assert len(reqs) == 2
    cliente, reqs = montar(httpx.ReadTimeout("t"), ok())
    assert pedir(cliente).datos == {"ok": True}
    assert len(reqs) == 2


def test_4xx_no_reintenta():
    cliente, reqs = montar(httpx.Response(401, text="no"), ok())
    with pytest.raises(ErrorModelo, match="401"):
        pedir(cliente)
    assert len(reqs) == 1


@pytest.mark.parametrize("contenido", ["", "   ", "no es json", "[1, 2]", None])
def test_contenido_invalido(contenido):
    cliente, _ = montar(ok(contenido))
    with pytest.raises(ErrorModelo):
        pedir(cliente)


def test_sin_choices_o_sin_costo():
    cliente, _ = montar(httpx.Response(200, json={"usage": {"cost": 0.1}}))
    with pytest.raises(ErrorModelo):
        pedir(cliente)
    cliente, _ = montar(ok(costo=None))
    with pytest.raises(ErrorModelo, match="usage.cost"):
        pedir(cliente)


def test_la_llave_no_sale_en_repr_ni_excepciones():
    cliente, _ = montar(httpx.ConnectError(f"fallo con {LLAVE}"), httpx.ConnectError("x"))
    assert LLAVE not in repr(cliente) and LLAVE not in str(vars(cliente).get("modelo_id"))
    with pytest.raises(ErrorModelo) as exc:
        pedir(cliente)
    assert LLAVE not in str(exc.value)
    assert LLAVE not in repr(exc.value)


def test_modelo_falso():
    falso = ModeloFalso([{"a": 1}, {"b": 2}], costo=0.5)
    r1 = asyncio.run(falso.pedir_json(sistema="s", usuario="u", esquema={}))
    r2 = asyncio.run(falso.pedir_json(sistema="s2", usuario="u2", esquema={}, imagen_png=b"x"))
    assert (r1.datos, r2.datos, r1.costo) == ({"a": 1}, {"b": 2}, 0.5)
    assert [c["sistema"] for c in falso.llamadas] == ["s", "s2"]
    assert falso.llamadas[1]["imagen_png"] == b"x"
    with pytest.raises(ErrorModelo):
        asyncio.run(falso.pedir_json(sistema="s", usuario="u", esquema={}))
