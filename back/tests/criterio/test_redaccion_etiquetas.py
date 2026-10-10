from app.criterio.redaccion import redactar

PASSWORD = "clave-falsa-9X7Q"


def test_borra_el_valor_tras_una_etiqueta_de_secreto():
    texto = "Clave de integración: SGC-41K8-77PX. No comparta esta clave."
    salida = redactar(texto, [])
    assert "SGC-41K8-77PX" not in salida
    assert "Clave de integración:" in salida


def test_etiquetas_con_igual_y_en_otros_idiomas():
    for t in (
        "token=abc123xyz",
        "API key: k-998877",
        "password: hunter2hunter2",
        "Contraseña: x9y8z7",
    ):
        assert "[secreto]" in redactar(t, [])


def test_no_toca_texto_sin_etiqueta():
    assert redactar("Tiene 3 facturas vencidas", []) == "Tiene 3 facturas vencidas"


def test_secreto_en_mayusculas_o_con_separadores():
    for variante in (PASSWORD.upper(), "clave falsa 9X7Q", "clave-falsa-9-X-7-Q"):
        salida = redactar(f"vi {variante} en pantalla", [PASSWORD]).lower()
        assert "falsa" not in salida


def test_secreto_corto_exacto_se_sigue_borrando():
    assert "abc1" not in redactar("el valor abc1 salió", ["abc1"])
