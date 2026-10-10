import asyncio

from app.agente.herramientas import _verbos_en, clic, tecla


def test_clic_no_puede_comprometer():
    for desc in ("el botón Guardar", "botón 'Eliminar cliente'", "enlace Exportar a Excel"):
        r = asyncio.run(clic(None, descripcion=desc))  # type: ignore[arg-type]
        assert not r.ok
        assert "confirmar" in r.observacion


def test_ctrl_s_no_se_pulsa_a_mano():
    for nombre in ("ctrl+s", "Ctrl + S", "ctrl+shift+s"):
        r = asyncio.run(tecla(None, nombre=nombre))  # type: ignore[arg-type]
        assert not r.ok and "confirmar" in r.observacion


def test_detecta_el_verbo_aunque_no_haya_tildes_ni_mayusculas():
    assert _verbos_en("BORRAR registro") == {"eliminar"}
    assert _verbos_en("Grabar") == {"guardar"}
    assert _verbos_en("campo Nombre") == set()
