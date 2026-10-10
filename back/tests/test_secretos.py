import logging
from pathlib import Path

from app.store import Store
from tests.conftest import AUTH, PASSWORD_FALSA, cuerpo_tarea, esperar_estado


def test_la_contrasena_no_aparece_en_ninguna_parte(client, settings, caplog):
    caplog.set_level(logging.DEBUG)
    salidas = []

    r = client.post("/tasks", json=cuerpo_tarea(), headers=AUTH)
    salidas.append(r.text)
    task_id = r.json()["task_id"]
    salidas.append(client.get(f"/tasks/{task_id}", headers=AUTH).text)
    salidas.append(str(esperar_estado(client, task_id, "fallida")))

    # Entrada inválida: el error de validación no debe repetir lo que se envió.
    malo = cuerpo_tarea(escritorio={"url": "ws://malo", "password": PASSWORD_FALSA})
    salidas.append(client.post("/tasks", json=malo, headers=AUTH).text)

    # Eventos guardados.
    salidas.append(str(Store(settings.db_path).eventos_desde(task_id)))

    for texto in salidas:
        assert PASSWORD_FALSA not in texto
    assert PASSWORD_FALSA not in caplog.text

    # Todo lo que quedó en disco junto a la base (SQLite y su journal).
    for archivo in Path(settings.db_path).parent.iterdir():
        assert PASSWORD_FALSA.encode() not in archivo.read_bytes(), archivo.name
