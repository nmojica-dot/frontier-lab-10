from fastapi.testclient import TestClient

from app.main import create_app
from app.store import Store
from tests.conftest import AUTH


def test_tarea_en_curso_al_arrancar_queda_fallida(settings):
    Store(settings.db_path).crear_tarea("vieja", "una tarea", "api", None)

    with TestClient(create_app(settings)) as c:
        r = c.get("/tasks/vieja", headers=AUTH)

    assert r.json()["estado"] == "fallida"
    assert "reiniciado" in r.json()["resumen"]
    eventos = Store(settings.db_path).eventos_desde("vieja")
    assert [e["event"] for e in eventos] == ["fin"]


def test_tarea_terminada_no_se_toca_al_arrancar(settings):
    store = Store(settings.db_path)
    store.crear_tarea("lista", "una tarea", "api", None)
    store.finalizar("lista", "terminada", "Hecho.")

    with TestClient(create_app(settings)) as c:
        r = c.get("/tasks/lista", headers=AUTH)

    assert r.json() == {"estado": "terminada", "resumen": "Hecho."}
