import asyncio
import json
import threading
import time

from app.main import create_app
from tests.conftest import AUTH, PASSWORD_FALSA, TOKEN, cuerpo_tarea, esperar_estado

JPEG = b"\xff\xd8\xff\xe0falso-jpeg"
PREGUNTA = {
    "pregunta_id": "p1",
    "tipo": "eleccion",
    "texto": "¿Cuál Ana Torres?",
    "candidatos": [{"id": "c1", "datos": {"ciudad": "Cali"}}, {"id": "c2", "datos": {}}],
}
CONFIRMACION = {
    "pregunta_id": "p2",
    "tipo": "confirmacion",
    "accion": "eliminar",
    "registro": {"nombre": "Ana Torres"},
}


def tarea_vacia(client) -> str:
    """Tarea sin worker: los eventos los inserta el test directo en el Store."""
    task_id = "t" + str(time.time_ns())
    client.app.state.store.crear_tarea(task_id, "x", "api", None)
    return task_id


def leer_sse(client, task_id: str, headers: dict | None = None, hasta_fin: bool = True) -> list:
    """Devuelve [(id, event, data)] hasta que el servidor cierre el stream."""
    out, actual = [], {}
    with client.stream(
        "GET", f"/tasks/{task_id}/eventos", headers={**AUTH, **(headers or {})}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        for linea in r.iter_lines():
            if linea.startswith(":"):
                continue
            if linea == "":
                if actual:
                    out.append((actual["id"], actual["event"], json.loads(actual["data"])))
                    actual = {}
                continue
            k, _, v = linea.partition(": ")
            actual[k] = v
    return out


def test_tarea_terminada_reenvia_todo_y_cierra_con_fin(client):
    task_id = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
    esperar_estado(client, task_id, "fallida")
    evs = leer_sse(client, task_id)
    assert [e[1] for e in evs] == ["estado", "paso", "fin"]
    assert [e[0] for e in evs] == ["1", "2", "3"]
    assert evs[-1][2]["estado"] == "fallida"


def test_last_event_id_no_repite_ni_pierde(client):
    task_id = tarea_vacia(client)
    store = client.app.state.store
    for n in range(1, 4):
        store.agregar_evento(task_id, "paso", {"n": n, "texto": f"paso {n}"})
    store.finalizar(task_id, "terminada", "ok")
    evs = leer_sse(client, task_id, {"Last-Event-ID": "2"})
    assert [e[0] for e in evs] == ["3", "4"]
    assert evs[-1][1] == "fin"


def test_last_event_id_basura_equivale_a_cero(client):
    task_id = tarea_vacia(client)
    client.app.state.store.finalizar(task_id, "terminada", "ok")
    assert [e[0] for e in leer_sse(client, task_id, {"Last-Event-ID": "abc"})] == ["1"]


def test_eventos_en_vivo_llegan_y_el_stream_cierra_tras_fin(client):
    task_id = tarea_vacia(client)
    store = client.app.state.store

    def productor():
        time.sleep(0.3)  # más que el latido: el cliente ya está esperando
        store.agregar_evento(task_id, "paso", {"n": 1, "texto": "hola"})
        time.sleep(0.1)
        store.finalizar(task_id, "terminada", "listo")

    hilo = threading.Thread(target=productor)
    hilo.start()
    evs = leer_sse(client, task_id)
    hilo.join()
    assert [e[1] for e in evs] == ["paso", "fin"]
    assert client.app.state.bus.n_suscriptores(task_id) == 0


def test_suscripcion_se_libera_si_el_cliente_se_va(settings):
    """TestClient no simula la desconexión a mitad de stream: se maneja ASGI directo."""
    app = create_app(settings)
    app.state.store.crear_tarea("t1", "x", "api", None)
    bus = app.state.bus

    async def escenario() -> None:
        recibidos: list[dict] = []
        pidio: list[int] = []
        desconectar = asyncio.Event()
        primera = asyncio.Event()

        async def receive() -> dict:
            if not pidio:
                pidio.append(1)
                return {"type": "http.request", "body": b"", "more_body": False}
            await desconectar.wait()
            return {"type": "http.disconnect"}

        async def send(msg: dict) -> None:
            recibidos.append(msg)
            if msg["type"] == "http.response.body" and msg.get("body"):
                primera.set()

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/tasks/t1/eventos",
            "query_string": b"",
            "headers": [(b"authorization", f"Bearer {TOKEN}".encode())],
            "http_version": "1.1",
            "scheme": "http",
            "server": ("t", 80),
            "client": ("t", 1),
        }
        corrida = asyncio.create_task(app(scope, receive, send))
        await asyncio.wait_for(primera.wait(), 3)  # llegó el primer latido
        assert bus.n_suscriptores("t1") == 1
        desconectar.set()
        await asyncio.wait_for(corrida, 3)
        assert bus.n_suscriptores("t1") == 0

    asyncio.run(escenario())


def test_eventos_exige_token_y_tarea(client):
    assert client.get("/tasks/x/eventos").status_code == 401
    r = client.get("/tasks/no-existe/eventos", headers=AUTH)
    assert r.status_code == 404
    assert r.json() == {
        "error": {"codigo": "tarea_no_existe", "mensaje": r.json()["error"]["mensaje"]}
    }


def _con_pregunta(client, pregunta=PREGUNTA, event="pregunta") -> str:
    task_id = tarea_vacia(client)
    client.app.state.store.registrar_pregunta(task_id, event, pregunta)
    return task_id


def test_pregunta_deja_en_espera_y_expone_pregunta(client):
    task_id = _con_pregunta(client)
    estado = client.get(f"/tasks/{task_id}", headers=AUTH).json()
    assert estado["estado"] == "en_curso"
    assert estado["subestado"] == "en_espera"
    assert estado["pregunta"]["pregunta_id"] == "p1"


def test_respuesta_valida_da_202_continua_y_entrega_al_worker(client):
    task_id = _con_pregunta(client)
    cuerpo = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "c2"}
    r = client.post(f"/tasks/{task_id}/respuesta", json=cuerpo, headers=AUTH)
    assert r.status_code == 202
    estado = client.get(f"/tasks/{task_id}", headers=AUTH).json()
    assert "subestado" not in estado and "pregunta" not in estado
    cola = client.app.state.respuestas._cola(task_id)
    assert cola.get_nowait() == {"pregunta_id": "p1", "valor": "c2"}
    store = client.app.state.store
    assert [e["event"] for e in store.eventos_desde(task_id)] == ["pregunta", "estado", "estado"]


def test_segunda_respuesta_es_409(client):
    task_id = _con_pregunta(client)
    cuerpo = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "c1"}
    assert client.post(f"/tasks/{task_id}/respuesta", json=cuerpo, headers=AUTH).status_code == 202
    r = client.post(f"/tasks/{task_id}/respuesta", json=cuerpo, headers=AUTH)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "pregunta_no_vigente"


def test_pregunta_vencida_o_ajena_es_409_sin_efecto(client):
    task_id = _con_pregunta(client)
    otra = {"pregunta_id": "otra", "tipo": "eleccion", "valor": "c1"}
    assert client.post(f"/tasks/{task_id}/respuesta", json=otra, headers=AUTH).status_code == 409
    assert client.get(f"/tasks/{task_id}", headers=AUTH).json()["subestado"] == "en_espera"
    client.app.state.store.finalizar(task_id, "fallida", "sin respuesta")
    ok = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "c1"}
    assert client.post(f"/tasks/{task_id}/respuesta", json=ok, headers=AUTH).status_code == 409


def test_respuesta_sin_pregunta_o_tarea_inexistente(client):
    cuerpo = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "c1"}
    r = client.post("/tasks/no-existe/respuesta", json=cuerpo, headers=AUTH)
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "tarea_no_existe"
    task_id = tarea_vacia(client)
    assert client.post(f"/tasks/{task_id}/respuesta", json=cuerpo, headers=AUTH).status_code == 409
    assert client.post(f"/tasks/{task_id}/respuesta", json=cuerpo).status_code == 401


def test_valor_invalido_es_422_y_no_consume_la_pregunta(client):
    task_id = _con_pregunta(client)
    malo = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "no-es-candidato"}
    r = client.post(f"/tasks/{task_id}/respuesta", json=malo, headers=AUTH)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "entrada_invalida"
    tipo = {"pregunta_id": "p1", "tipo": "confirmacion", "valor": True}
    assert client.post(f"/tasks/{task_id}/respuesta", json=tipo, headers=AUTH).status_code == 422
    bueno = {"pregunta_id": "p1", "tipo": "eleccion", "valor": "c1"}
    assert client.post(f"/tasks/{task_id}/respuesta", json=bueno, headers=AUTH).status_code == 202


def test_confirmacion_acepta_booleano(client):
    task_id = _con_pregunta(client, CONFIRMACION, "confirmacion")
    texto = {"pregunta_id": "p2", "tipo": "confirmacion", "valor": "si"}
    assert client.post(f"/tasks/{task_id}/respuesta", json=texto, headers=AUTH).status_code == 422
    no = {"pregunta_id": "p2", "tipo": "confirmacion", "valor": False}
    assert client.post(f"/tasks/{task_id}/respuesta", json=no, headers=AUTH).status_code == 202
    cola = client.app.state.respuestas._cola(task_id)
    assert cola.get_nowait()["valor"] is False


def test_pantalla_204_sin_cuadro_y_jpeg_con_cuadro(client):
    task_id = tarea_vacia(client)
    assert client.get(f"/tasks/{task_id}/pantalla.jpg", headers=AUTH).status_code == 204
    client.app.state.cuadros.guardar_pantalla(task_id, JPEG)
    r = client.get(f"/tasks/{task_id}/pantalla.jpg", headers=AUTH)
    assert r.status_code == 200 and r.content == JPEG
    assert r.headers["content-type"] == "image/jpeg"
    assert client.get("/tasks/no-existe/pantalla.jpg", headers=AUTH).status_code == 404
    assert client.get(f"/tasks/{task_id}/pantalla.jpg").status_code == 401


def test_capturas_se_guardan_en_disco_y_se_sirven(client, settings):
    task_id = tarea_vacia(client)
    client.app.state.cuadros.guardar_captura(task_id, 3, JPEG)
    r = client.get(f"/tasks/{task_id}/capturas/3.jpg", headers=AUTH)
    assert r.status_code == 200 and r.content == JPEG
    assert client.get(f"/tasks/{task_id}/capturas/4.jpg", headers=AUTH).status_code == 404
    assert client.get(f"/tasks/{task_id}/capturas/3.jpg").status_code == 401


def test_cuadros_rechaza_lo_que_no_es_jpeg(client):
    import pytest

    with pytest.raises(ValueError):
        client.app.state.cuadros.guardar_pantalla("t", b"no-es-jpeg")


def test_la_contrasena_no_aparece_en_los_eventos(client):
    task_id = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH).json()["task_id"]
    esperar_estado(client, task_id, "fallida")
    assert PASSWORD_FALSA not in json.dumps(leer_sse(client, task_id))
