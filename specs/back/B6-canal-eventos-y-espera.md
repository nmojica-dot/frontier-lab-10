# Spec: B6 · Canal de eventos, preguntas y espera

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §7 "Seguir la tarea en vivo", §11 Dudas, §13

## 1. Qué es y por qué
Lo que alimenta al front: eventos en vivo y el mecanismo de pausar la tarea para preguntar a la persona y retomarla. Implementa la mitad del servidor del [contrato](../00-contrato-back-front.md).

## 2. Decisiones firmes
- **SSE** en `GET /tasks/{id}/eventos`, eventos y formas exactos del contrato §2.
- **Pregunta o confirmación:** el worker emite el evento, guarda `pregunta_id` y queda en `subestado:"en_espera"`. Antes de esperar, **suelta el escritorio** (cierra RFB).
- **Respuesta:** `POST /tasks/{id}/respuesta` valida que la pregunta sea la vigente. Si lo es, reconecta, comprueba que el registro siga igual y continúa. Si cambió, se detiene y muestra qué cambió.
- **Por API (`canal:"api"`):** nunca se pregunta; duda → `fallida` con datos; eliminar → directo.
- **Capturas:** cada `paso` y `evidencia` puede traer `captura` (n); se guardan en disco como JPEG y se sirven por `/capturas/{n}.jpg`.
- **Pantalla en vivo:** `pantalla.jpg` sirve el último cuadro capturado por B2.
- **Tiempo en espera:** el reloj de 5 min se pausa mientras espera; hay un tope de espera total (propuesto: 30 min) tras el cual la tarea pasa a `fallida` ("sin respuesta").

## 3. Decisiones abiertas
- [ ] ¿Reloj nuevo al retomar? (PRD §17). Propuesto: se continúa el reloj pausado.
- [ ] Tope de espera: ¿30 min?

## 4. Descartado
Mantener el escritorio conectado mientras se espera (lo ocupa sin usarlo).

## 5. Edge cases
- Dos respuestas seguidas a la misma pregunta: la primera gana, la segunda `409`.
- Persona responde "no" a una confirmación: no se elimina; `terminada` con resumen "no se eliminó por decisión de la persona".
- Al retomar, el registro desapareció: `fallida` explicando qué cambió.

## 6. Fuera de scope
Notificaciones push, Telegram (P1).

## 7. Referencias
`PRD.md` §11, §13 · `specs/00-contrato-back-front.md`

## Verificación
Cliente SSE de texto (`curl -N`): ver `paso`, `pregunta`, responder por `POST`, ver continuar y `fin`. Reconectar con `Last-Event-ID` sin perder eventos.
