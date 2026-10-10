import asyncio
from typing import Any

import pytest

from app.agente.contrato import ContratoInvalido, fijar_contrato, normalizar
from app.agente.tipos import RespuestaModelo


class _Falso:
    def __init__(self, datos: dict[str, Any]) -> None:
        self.datos = datos
        self.llamadas: list[dict[str, Any]] = []

    async def pedir_json(self, *, sistema, usuario, esquema, imagen_png=None):
        self.llamadas.append({"usuario": usuario, "imagen": imagen_png})
        return RespuestaModelo(datos=self.datos, costo=0.0)


def _datos(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "tipo": "consultar",
        "registro_objetivo": {},
        "valores_a_escribir": {},
        "filtros": {},
        "pregunta": None,
        "borrado_masivo": False,
        "verbos": [],
    }
    return base | kw


def _fijar(instruccion: str, **kw: Any):
    modelo = _Falso(_datos(**kw))
    contrato = asyncio.run(fijar_contrato(instruccion, modelo))
    assert modelo.llamadas[0]["imagen"] is None
    return contrato


def test_e1_crear_cliente():
    c = _fijar(
        "Registra al cliente Papelería Los Andes, NIT 901234567, teléfono 3157654321, ciudad Pereira.",
        tipo="crear",
        valores_a_escribir={
            "nombre": "Papelería Los Andes",
            "nit": "901234567",
            "telefono": "3157654321",
            "ciudad": "Pereira",
        },
    )
    assert c.valores_permitidos["nit"] == ("901234567",)
    assert c.verbos_permitidos == {"guardar"}


def test_e2_cambiar_direccion():
    c = _fijar(
        "Corrige la dirección del cliente Distribuciones El Faro: ahora es Calle 80 # 24-15.",
        tipo="cambiar",
        registro_objetivo={"nombre": "Distribuciones El Faro"},
        valores_a_escribir={"direccion": "Calle 80 # 24-15"},
    )
    assert c.registro_objetivo == {"nombre": "Distribuciones El Faro"}
    assert c.valores_permitidos == {"direccion": ("Calle 80 # 24-15",)}


def test_e3_consulta_sin_compromisos():
    c = _fijar(
        "¿Cuántas facturas vencidas tiene Ferretería Ruiz?",
        registro_objetivo={"nombre": "Ferretería Ruiz"},
        pregunta="¿Cuántas facturas vencidas tiene Ferretería Ruiz?",
        verbos=["guardar"],
    )
    assert c.verbos_permitidos == frozenset()
    assert c.valores_permitidos == {}
    assert c.pregunta


def test_e4_exportar_con_filtros_calculados():
    c = _fijar(
        "Exporta el reporte de pedidos entregados en septiembre de 2026.",
        tipo="exportar",
        filtros={"estado": "Entregado", "desde": "2026-09-01", "hasta": "2026-09-30"},
    )
    assert c.verbos_permitidos == {"exportar"}
    assert c.valores_permitidos["desde"] == ("2026-09-01",)


def test_e5_homonimos_no_inventa_documento():
    c = _fijar(
        "Cambia el teléfono de Ana Torres a 3014445566.",
        tipo="cambiar",
        registro_objetivo={"nombre": "Ana Torres"},
        valores_a_escribir={"telefono": "3014445566"},
    )
    assert c.registro_objetivo == {"nombre": "Ana Torres"}


def test_normaliza_para_comparar_solo():
    c = _fijar(
        "Cambia la ciudad de Ana a  PEREIRA",
        tipo="cambiar",
        registro_objetivo={"nombre": "Ana"},
        valores_a_escribir={"ciudad": "Pereira"},
    )
    assert c.valores_permitidos["ciudad"] == ("Pereira",)
    assert normalizar("  Papelería\tLOS  Andes ") == "papeleria los andes"


@pytest.mark.parametrize(
    "instruccion,kw",
    [
        (
            "Cambia el teléfono de Ana Torres a 3014445566.",
            {"tipo": "cambiar", "valores_a_escribir": {"telefono": "3000000000"}},
        ),
        (
            "Cambia el teléfono de Ana Torres a 3014445566.",
            {
                "tipo": "cambiar",
                "registro_objetivo": {"documento": "52345678"},
                "valores_a_escribir": {"telefono": "3014445566"},
            },
        ),
        ("¿Cuántas facturas hay?", {"tipo": "consultar", "valores_a_escribir": {"x": "facturas"}}),
        ("Cambia el teléfono de Ana.", {"tipo": "cambiar"}),
        ("Hola", {"tipo": "bailar"}),
        ("Cambia el teléfono de Ana a 301.", {"tipo": "cambiar", "valores_a_escribir": {"t": " "}}),
    ],
)
def test_rechaza_valores_inventados_o_incoherentes(instruccion, kw):
    with pytest.raises(ContratoInvalido):
        _fijar(instruccion, **kw)


def test_respuesta_malformada_se_rechaza():
    with pytest.raises(ContratoInvalido):
        _fijar("Cambia algo", tipo="cambiar", valores_a_escribir=["x"])


def test_borrado_masivo_queda_marcado_para_b4():
    c = _fijar(
        "Elimina todos los clientes de Cali.",
        tipo="eliminar",
        registro_objetivo={"ciudad": "Cali"},
        borrado_masivo=True,
        verbos=["eliminar"],
    )
    assert "eliminar" not in c.verbos_permitidos
    assert c.registro_objetivo == {}


def test_eliminar_uno_permite_solo_eliminar():
    c = _fijar(
        "Elimina el cliente con documento 52345678.",
        tipo="eliminar",
        registro_objetivo={"documento": "52345678"},
    )
    assert c.verbos_permitidos == {"eliminar"}


def test_el_modelo_no_cuela_verbos():
    c = _fijar(
        "Cambia el teléfono de Ana a 301.",
        tipo="cambiar",
        registro_objetivo={"nombre": "Ana"},
        valores_a_escribir={"telefono": "301"},
        verbos=["guardar", "eliminar", "exportar"],
    )
    assert c.verbos_permitidos == {"guardar"}
