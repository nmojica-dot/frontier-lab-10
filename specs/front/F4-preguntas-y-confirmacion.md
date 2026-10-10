# Spec: F4 · Preguntas con contexto y confirmación de eliminar

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §8 P0 front, §13, §15

## 1. Qué es y por qué
Cuando Navegante duda o va a eliminar, la persona decide con lo que se le muestra, sin abrir el sistema viejo. Es donde se cumple "cero errores silenciosos" desde la interfaz.

## 2. Decisiones firmes
- **Pregunta (`pregunta`):** tarjeta en el chat con el texto y una tarjeta por candidato mostrando sus `datos` (los que los distinguen). La persona elige uno; el front envía `POST /respuesta` con `{pregunta_id, tipo:"eleccion", valor: id}`.
- **Confirmación (`confirmacion`):** tarjeta con el registro completo y dos botones, "Eliminar" y "Cancelar". "Eliminar" usa `button-primary` (`tertiary`) y "Cancelar" `button-tertiary`; el diseño no define color destructivo ni de error y la regla es "nunca colores fuera de la paleta", así que la gravedad se comunica con el texto y la tarjeta del registro, no con rojo. "Cancelar" tiene el foco por defecto.
- **Una sola respuesta:** tras enviar, la tarjeta queda inactiva y muestra lo elegido. Doble clic no envía dos veces.
- **`409 pregunta_no_vigente`:** la tarjeta se marca como "ya no aplica" (la tarea siguió o terminó) sin error técnico.
- **Mientras espera:** estado visible "esperando tu respuesta"; el escritorio en vivo (F2) queda congelado y etiquetado.
- **Retomar:** al recargar con una pregunta pendiente (`GET /tasks/{id}` trae `pregunta`), la tarjeta reaparece.
- **Accesible:** las opciones son botones reales, navegables con teclado.

## 3. Decisiones abiertas
- [ ] ¿Hace falta un color de error/destructivo? Consultar con quien lleva el diseño; hasta entonces se usa solo la paleta.
- [ ] ¿La tarea en espera se cancela desde el front? No es P0; se anota por si la espera se alarga (tope en B6).

## 4. Descartado
Elegir por texto libre ("la primera"). Confirmar eliminar con un checkbox.

## 5. Edge cases
- Candidatos con datos idénticos en lo visible: se muestran todos los campos que envía el back; el front no decide cuáles ocultar.
- Persona cierra la pestaña: la tarea queda en espera en el back (B6); al volver con el mismo `task_id` retoma.
- Sin conexión al responder: reintento manual, la tarjeta sigue activa.

## 6. Fuera de scope
Notificaciones fuera de la pestaña, respuestas por Telegram (P1).

## 7. Referencias
`PRD.md` §13, §15 · `specs/00-contrato-back-front.md` · `specs/back/B6-canal-eventos-y-espera.md` · `DESIGN.md`

## Verificación
Escenario E5 (dos "Ana Torres"): aparecen ambas con sus datos y la tarea no avanza hasta elegir. Eliminar por chat: sin pulsar nada, nada se borra. Doble clic en un candidato envía una sola respuesta.
