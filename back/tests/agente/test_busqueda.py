from app.agente.herramientas import _es_filtro_de_lectura, _literal_del_contrato, _tabla_texto
from app.criterio.contrato import ContratoCambios

CONSULTA = ContratoCambios(registro_objetivo={"nombre": "Ferretería Ruiz"}, pregunta="¿cuántas?")
CAMBIO = ContratoCambios(
    registro_objetivo={"nombre": "Ana Torres"},
    valores_permitidos={"telefono": ("3014445566",)},
    verbos_permitidos=frozenset({"guardar"}),
)


def test_el_texto_sin_tilde_se_corrige_con_el_literal_de_la_instruccion():
    assert _literal_del_contrato(CONSULTA, "Ferreteria Ruiz") == "Ferretería Ruiz"
    assert _literal_del_contrato(CONSULTA, "ferretería ruiz") == "Ferretería Ruiz"


def test_un_texto_que_no_esta_en_la_instruccion_no_se_corrige():
    assert _literal_del_contrato(CONSULTA, "Otra Ferretería") is None


def test_en_una_consulta_se_puede_filtrar_con_el_valor_o_parte_de_el():
    assert _es_filtro_de_lectura(CONSULTA, "Ferretería Ruiz")
    assert _es_filtro_de_lectura(CONSULTA, "Ruiz")


def test_en_una_consulta_no_se_escribe_un_valor_ajeno():
    assert not _es_filtro_de_lectura(CONSULTA, "Pedro Pérez")
    assert not _es_filtro_de_lectura(CONSULTA, "")


def test_si_la_tarea_puede_guardar_se_exige_la_validacion_estricta():
    assert not _es_filtro_de_lectura(CAMBIO, "3014445566")


def test_la_tabla_en_texto_trae_las_filas_y_un_conteo_calculado_por_estado():
    filas = [
        {"Código": "F1", "Cliente": "Ferretería Ruiz", "Estado": "Vencida"},
        {"Código": "F2", "Cliente": "Ferretería Ruiz", "Estado": "Pagada"},
        {"Código": "F3", "Cliente": "Ferretería Ruiz", "Estado": "Vencida"},
    ]
    texto = _tabla_texto(filas)
    assert "F1 | Ferretería Ruiz | Vencida" in texto
    assert "Pagada=1, Vencida=2" in texto


def test_tabla_vacia_y_tabla_larga_recortada():
    assert _tabla_texto([]) == "(sin filas)"
    muchas = [{"Código": f"F{i}", "Detalle": "x" * 80} for i in range(200)]
    assert "(...recortado)" in _tabla_texto(muchas)
