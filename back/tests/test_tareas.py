import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import AUTH, TOKEN, cuerpo_tarea, esperar_estado


def test_crear_tarea_responde_rapido_y_con_task_id(client):
    inicio = time.perf_counter()
    r = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH)
    assert time.perf_counter() - inicio < 2
    assert r.status_code == 200
    assert set(r.json()) == {"task_id"}


def test_estado_tiene_solo_valores_del_contrato(client):
    task_id = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
    r = client.get(f"/tasks/{task_id}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["estado"] in {"en_curso", "terminada", "fallida"}
    assert "resumen" in r.json()


def test_worker_de_mentira_termina_fallida_y_no_finge_exito(client):
    task_id = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
    final = esperar_estado(client, task_id, "fallida")
    assert "no se ejecutó" in final["resumen"]


def test_canal_y_solicitante_opcionales(client):
    body = cuerpo_tarea(canal="chat", solicitante="chat-web")
    assert client.post("/tasks", json=body, headers=AUTH).status_code == 200


def test_tarea_inexistente_es_404(client):
    r = client.get("/tasks/no-existe", headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "tarea_no_existe"
    assert set(r.json()["error"]) == {"codigo", "mensaje"}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tarea": "hola"},
        cuerpo_tarea(escritorio={"url": "ws://escritorio.ejemplo/websockify", "password": "x"}),
        cuerpo_tarea(escritorio={"url": "https://escritorio.ejemplo", "password": "x"}),
        cuerpo_tarea(escritorio={"url": "wss://", "password": "x"}),
        cuerpo_tarea(escritorio={"url": "wss://escritorio.ejemplo/websockify", "password": ""}),
        cuerpo_tarea(escritorio={"url": "wss://escritorio.ejemplo/websockify"}),
        cuerpo_tarea(tarea="   "),
        cuerpo_tarea(canal="telegram"),
    ],
)
def test_entrada_invalida_es_422(client, cuerpo):
    r = client.post("/tasks", json=cuerpo, headers=AUTH)
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "entrada_invalida"


def test_cuerpo_que_no_es_json_es_422(client):
    r = client.post(
        "/tasks", content="no soy json", headers={**AUTH, "Content-Type": "application/json"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "entrada_invalida"


def test_segunda_tarea_al_mismo_escritorio_espera(tmp_path):
    settings = Settings(api_token=TOKEN, db_path=str(tmp_path / "t.db"), worker_demora=0.4)
    with TestClient(create_app(settings)) as c:
        a = c.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
        b = c.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
        time.sleep(0.2)
        # A está trabajando y B espera su turno: ninguna terminó.
        assert c.get(f"/tasks/{a}", headers=AUTH).json()["estado"] == "en_curso"
        assert c.get(f"/tasks/{b}", headers=AUTH).json()["estado"] == "en_curso"
        esperar_estado(c, a, "fallida")
        assert c.get(f"/tasks/{b}", headers=AUTH).json()["estado"] == "en_curso"
        esperar_estado(c, b, "fallida")


def test_tareas_de_escritorios_distintos_corren_a_la_vez(tmp_path):
    settings = Settings(api_token=TOKEN, db_path=str(tmp_path / "t.db"), worker_demora=0.4)
    with TestClient(create_app(settings)) as c:
        otro = cuerpo_tarea(escritorio={"url": "wss://otro.ejemplo/websockify", "password": "x"})
        a = c.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
        b = c.post("/tasks", json=otro, headers=AUTH).json()["task_id"]
        esperar_estado(c, a, "fallida")
        # B arrancó junto con A: si hubiera esperado turno tardaría otros 0.4 s.
        esperar_estado(c, b, "fallida", timeout=0.3)
