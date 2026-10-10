import pytest

from app.config import Settings
from app.main import create_app
from tests.conftest import AUTH, cuerpo_tarea

RUTAS = [
    ("get", "/health", None),
    ("post", "/tasks", cuerpo_tarea()),
    ("get", "/tasks/cualquiera", None),
]


def test_health_con_token(client):
    r = client.get("/health", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


@pytest.mark.parametrize("metodo,ruta,cuerpo", RUTAS)
def test_sin_token_es_401(client, metodo, ruta, cuerpo):
    r = getattr(client, metodo)(ruta, json=cuerpo) if cuerpo else getattr(client, metodo)(ruta)
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "no_autorizado"


@pytest.mark.parametrize(
    "cabecera", ["Bearer otro", "Basic token-de-prueba", "token-de-prueba", "Bearer "]
)
def test_token_invalido_es_401(client, cabecera):
    r = client.get("/health", headers={"Authorization": cabecera})
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "no_autorizado"


def test_401_gana_sobre_422(client):
    r = client.post("/tasks", json={"basura": 1})
    assert r.status_code == 401


def test_sin_api_token_configurado_no_arranca(tmp_path):
    with pytest.raises(RuntimeError, match="API_TOKEN"):
        create_app(Settings(api_token="", db_path=str(tmp_path / "t.db")))
