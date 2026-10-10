# Navegante · back

API que recibe una tarea en lenguaje natural y la ejecuta sobre un escritorio remoto, solo por pantalla (RFB, mouse y teclado). Responde `terminada` o `fallida` con un resumen sin secretos.

## Rutas
Todas piden `Authorization: Bearer <token del equipo>`.

| Ruta | Para qué |
|---|---|
| `GET /health` | `{"ok": true}` |
| `POST /tasks` | `{"tarea": "...", "escritorio": {"url": "wss://.../websockify", "password": "..."}}` → `{"task_id": "..."}` en menos de 2 s |
| `GET /tasks/{id}` | `{"estado": "en_curso\|terminada\|fallida", "resumen": "..."}` |
| `GET /tasks/{id}/eventos` | SSE con pasos y evidencias (para el front) |
| `GET /tasks/{id}/pantalla.jpg`, `/capturas/{n}.jpg`, `POST /tasks/{id}/respuesta` | Pantalla en vivo, evidencias y respuesta a preguntas |

El contrato completo con el front está en `specs/00-contrato-back-front.md`.

## Variables de entorno
Ver `.env.example`. Nada de esto se commitea.

| Variable | Qué es |
|---|---|
| `API_TOKEN` | Token del equipo. Sin él, el servicio no arranca. |
| `OPENROUTER_API_KEY` | Llave del modelo. Sin ella corre un worker de mentira que termina siempre `fallida`. |
| `MODELO_ID` | Modelo en OpenRouter. Por defecto `anthropic/claude-sonnet-5.5`; la prueba usa `anthropic/claude-haiku-5.5`. |
| `COSTO_MAX_POR_TAREA` | Tope en dólares; al pasarlo la tarea termina `fallida`. |
| `DB_PATH`, `CUADROS_DIR` | SQLite y carpeta de capturas. |

La contraseña del escritorio no es una variable: llega en cada `POST /tasks` y vive solo en memoria.

## Correr
```
cd back
uv sync
API_TOKEN=un-token-local uv run uvicorn app.main:create_app --factory --reload
```
En Railway: Root Directory `back`; el comando de arranque está en `railway.json`.

## Verificar
```
uv run pytest -q                       # 165 pruebas, sin red ni escritorio real
uv run ruff check . && uv run ruff format --check .
```
Contra el escritorio real, desde tu propia terminal (las claves se piden sin mostrarse):
```
export ESCRITORIO_URL='wss://.../websockify'
read -s ESCRITORIO_PASSWORD && export ESCRITORIO_PASSWORD
read -s ESCRITORIO_TOKEN && export ESCRITORIO_TOKEN
read -s OPENROUTER_API_KEY && export OPENROUTER_API_KEY
export MODELO_ID='anthropic/claude-haiku-5.5'
uv run python -m app.agente E5        # también E1..E4; imprime estado, resumen, costo y pasos
```

## Cómo está hecho
`app/rfb/` cliente RFB propio · `app/agente/` contrato de cambios, herramientas, ciclo y cliente de OpenRouter · `app/criterio/` reglas de seguridad, redacción de secretos y decisión del estado final · `app/store.py` SQLite · `app/bus.py` y `app/cuadros.py` canal de eventos y capturas.

Reglas que el código hace cumplir: solo se cambia lo que sale de la instrucción; Guardar, Exportar y Eliminar se ejecutan una sola vez; sin evidencia nunca hay `terminada`; ante la duda, `fallida` con los datos; el resumen sale sin secretos; desde 3:45 no empieza ningún compromiso y a 4:30 se cierra.
