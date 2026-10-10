# Spec: B1 · API de tareas

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §8 P0 back, §14

## 1. Qué es y por qué
Servicio FastAPI desplegado que cumple el contrato del reto y el [contrato back↔front](../00-contrato-back-front.md). Es lo que evalúa el jurado, así que se construye primero y funciona aunque el agente aún sea un esqueleto.

## 2. Decisiones firmes
- **Stack:** Python + FastAPI, tareas en segundo plano con `asyncio`, estado en memoria + SQLite (tareas y eventos). Sin Redis.
- **Rutas:** las de la tabla del contrato. Token por dependencia de FastAPI; sin token o inválido → 401 en todas.
- **`POST /tasks`:** valida, crea `task_id`, lanza el worker y responde. Nada de trabajo pesado antes de responder (< 2 s).
- **Un worker por tarea**, con reloj propio (ver B3). Una sola tarea activa por escritorio.
- **Eventos:** cada evento se guarda en SQLite con `seq` y se publica a los suscriptores SSE. `Last-Event-ID` lee desde la tabla.
- **Secretos:** `escritorio.password` vive solo en memoria del worker; no se escribe en SQLite, ni en logs, ni en eventos.
- **Configuración por entorno:** `API_TOKEN`, `OPENROUTER_API_KEY`, tope de costo por tarea.

## 3. Decisiones abiertas
- [ ] Tareas en paralelo: si llegan 2 al mismo escritorio, ¿se encola o `fallida`? (pregunta a staff). Mientras tanto: la segunda espera.
- [ ] Host: Railway sin suspensión (propuesto).

## 4. Descartado
Redis o cola externa (una tarea a la vez no lo justifica). Guardar la contraseña para "reintentar" (riesgo de secreto sin beneficio).

## 5. Edge cases
- `POST /tasks` sin `escritorio` o con URL que no es `wss://` → 422.
- Reinicio del servicio con tareas `en_curso`: al arrancar se marcan `fallida` con "servicio reiniciado".
- Cliente SSE que se desconecta: se libera la suscripción, la tarea sigue.

## 6. Fuera de scope
Autenticación por usuario, límites por cliente, métricas.

## 7. Referencias
`PRD.md` §8, §14 · `CONTEXTO.md` "Qué piden"

## Verificación
- `GET /health` → 200 con token.
- `POST /tasks` responde < 2 s con el worker aún sin implementar.
- Sin token en cualquier ruta → 401.
- Buscar la contraseña de prueba en logs, DB y respuestas: no aparece.
