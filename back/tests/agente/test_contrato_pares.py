import asyncio

import pytest

from app.agente.contrato import ContratoInvalido, fijar_contrato
from app.agente.falso import ModeloFalso

INSTRUCCION = "Cambia el teléfono de Ana Torres a 3014445566."


def contrato(respuesta: dict):
    return asyncio.run(fijar_contrato(INSTRUCCION, ModeloFalso([respuesta])))


def base(**cambios) -> dict:
    d = {
        "tipo": "cambiar",
        "registro_objetivo": [{"campo": "nombre", "valor": "Ana Torres"}],
        "valores_a_escribir": [{"campo": "telefono", "valor": "3014445566"}],
        "filtros": [],
        "pregunta": None,
        "borrado_masivo": False,
        "verbos": ["guardar"],
    }
    d.update(cambios)
    return d


def test_acepta_listas_de_pares():
    c = contrato(base())
    assert c.registro_objetivo == {"nombre": "Ana Torres"}
    assert c.valores_permitidos == {"telefono": ("3014445566",)}
    assert c.verbos_permitidos == {"guardar"}


def test_un_valor_inventado_en_pares_se_rechaza():
    mal = base(valores_a_escribir=[{"campo": "telefono", "valor": "3000000000"}])
    with pytest.raises(ContratoInvalido, match="no aparece"):
        contrato(mal)


def test_pares_mal_formados_se_rechazan():
    with pytest.raises(ContratoInvalido, match="mal formado"):
        contrato(base(valores_a_escribir=[{"nombre": "x"}]))


def test_cambiar_sin_valores_sigue_siendo_invalido():
    with pytest.raises(ContratoInvalido, match="qué valores"):
        contrato(base(valores_a_escribir=[]))
