import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "token-de-prueba"
PASSWORD_FALSA = "clave-falsa-9X7Q"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def cuerpo_tarea(**cambios) -> dict:
    cuerpo = {
        "tarea": "Corrige la dirección de la cliente Ana Torres",
        "escritorio": {"url": "wss://escritorio.ejemplo/websockify", "password": PASSWORD_FALSA},
    }
    cuerpo.update(cambios)
    return cuerpo


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(api_token=TOKEN, db_path=str(tmp_path / "t.db"), worker_demora=0)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def esperar_estado(client: TestClient, task_id: str, estado: str, timeout: float = 3.0) -> dict:
    limite = time.time() + timeout
    cuerpo: dict = {}
    while time.time() < limite:
        cuerpo = client.get(f"/tasks/{task_id}", headers=AUTH).json()
        if cuerpo["estado"] == estado:
            return cuerpo
        time.sleep(0.02)
    raise AssertionError(f"La tarea no llegó a {estado}: {cuerpo}")
