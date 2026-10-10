from decimal import Decimal

import pytest

from app.criterio import (
    ContratoCambios,
    EntradaEstado,
    EntradaResumen,
    Evidencia,
    SecretoSinRedactar,
    armar_resumen,
    decidir_estado,
    linea_respuesta,
    redactar,
    redactar_datos,
)

PASSWORD = "clave-falsa-9X7Q"
TOKEN = "token-de-prueba"
LLAVE = "sk-or-llave-falsa-123456"
SECRETOS = [PASSWORD, TOKEN, LLAVE]


def test_resumen_no_contiene_secretos():
    entrada = EntradaResumen(
        estado="fallida",
        hecho=(f"Escribí la clave {PASSWORD} en el login",),
        motivos=(f"Falló con el token {TOKEN}",),
        notas_app_ignoradas=(f"Nota: usa {LLAVE}",),
        no_confirmado=(f"url%20{PASSWORD}",),
    )
    texto = armar_resumen(entrada, SECRETOS)
    for s in SECRETOS:
        assert s not in texto
    assert "[secreto]" in texto


def test_redactar_variantes_codificadas_y_patron_de_llave():
    texto = 'a=clave%2Dfalsa&b="clave-falsa-9X7Q" y sk-or-otra-llave-999999'
    salida = redactar(texto, ["clave-falsa-9X7Q"])
    assert "9X7Q" not in salida and "otra-llave" not in salida


def test_redactar_con_caracteres_especiales():
    clave = 'fa"lsa\\9X 7Q#'
    assert "9X" not in redactar(f"x {clave} y", [clave])


def test_secreto_vacio_es_error_explicito():
    with pytest.raises(ValueError):
        redactar("hola", [""])


def test_redactar_datos_anidados():
    carga = {"paso": f"tecleé {PASSWORD}", "lista": [TOKEN, 3], PASSWORD: True}
    salida = redactar_datos(carga, SECRETOS)
    assert PASSWORD not in repr(salida) and TOKEN not in repr(salida)
    assert salida["lista"][1] == 3


def test_secreto_sin_redactar_lanza(monkeypatch):
    import app.criterio.redaccion as r

    monkeypatch.setattr(r, "MARCA", PASSWORD)  # la marca reintroduce el secreto
    with pytest.raises(SecretoSinRedactar):
        r.redactar(f"x {PASSWORD}", [PASSWORD])


def test_linea_respuesta():
    assert linea_respuesta(()) is None
    assert linea_respuesta((1234567,)) == "respuesta: 1234567"
    assert linea_respuesta(("Medellín", 12)) == "respuesta: 12; Medellín"
    assert linea_respuesta((Decimal("1500.50"), 3.0)) == "respuesta: 1500.5; 3"
    with pytest.raises(ValueError):
        linea_respuesta((1, 2, 3))
    with pytest.raises(ValueError):
        linea_respuesta(("a\nb",))


def test_resumen_con_respuesta_y_sin_ella():
    con = armar_resumen(EntradaResumen(estado="terminada", respuesta=(42,)), SECRETOS)
    assert con.splitlines()[-1] == "respuesta: 42"
    sin = armar_resumen(EntradaResumen(estado="terminada"), SECRETOS)
    assert "respuesta:" not in sin


def test_resumen_estado_invalido():
    with pytest.raises(ValueError):
        armar_resumen(EntradaResumen(estado="en_curso"), SECRETOS)


ESCRITURA = ContratoCambios(
    valores_permitidos={"direccion": ("Calle 10 # 5-20",)},
    verbos_permitidos=frozenset({"guardar"}),
)
OK_POST = Evidencia(descripcion="Reabrí el registro", confirmada=True, posterior_a_compromiso=True)


def test_terminada_con_evidencia_posterior():
    r = decidir_estado(
        EntradaEstado(contrato=ESCRITURA, evidencias=(OK_POST,), compromisos=("guardar",))
    )
    assert r.estado == "terminada"


def test_nunca_terminada_sin_evidencia():
    r = decidir_estado(EntradaEstado(contrato=ESCRITURA, compromisos=("guardar",)))
    assert r.estado == "fallida" and r.motivos


@pytest.mark.parametrize(
    "cambio",
    [
        {"bloqueos": ("Borrado masivo bloqueado",)},
        {"no_confirmado": ("la dirección guardada",)},
        {"tiempo_agotado": True},
        {"tope_costo_excedido": True},
        {"error": "RFB se cayó"},
        {"compromisos": ("guardar", "guardar")},
        {"compromisos": ("eliminar",)},
        {
            "evidencias": (
                Evidencia(descripcion="x", confirmada=False, posterior_a_compromiso=True),
            )
        },
        {"evidencias": (Evidencia(descripcion="previa", confirmada=True),)},
    ],
)
def test_cualquier_duda_es_fallida(cambio):
    base = {"contrato": ESCRITURA, "evidencias": (OK_POST,), "compromisos": ("guardar",)}
    base.update(cambio)
    r = decidir_estado(EntradaEstado(**base))
    assert r.estado == "fallida" and r.motivos


def test_escritura_sin_compromiso_exige_justificacion():
    ev = (Evidencia(descripcion="El registro ya tenía el valor", confirmada=True),)
    assert decidir_estado(EntradaEstado(contrato=ESCRITURA, evidencias=ev)).estado == "fallida"
    r = decidir_estado(
        EntradaEstado(
            contrato=ESCRITURA, evidencias=ev, sin_cambios_justificados="ya tenía el valor"
        )
    )
    assert r.estado == "terminada"


def test_lectura_exige_respuesta_o_sin_respuesta_posible():
    c = ContratoCambios(pregunta="¿Cuántos clientes hay en Cali?")
    ev = (Evidencia(descripcion="Conté 7 filas en todas las páginas", confirmada=True),)
    assert decidir_estado(EntradaEstado(contrato=c, evidencias=ev)).estado == "fallida"
    assert (
        decidir_estado(EntradaEstado(contrato=c, evidencias=ev, respuesta=(7,))).estado
        == "terminada"
    )
    r = decidir_estado(EntradaEstado(contrato=c, evidencias=ev, sin_respuesta_posible=True))
    assert r.estado == "terminada"
