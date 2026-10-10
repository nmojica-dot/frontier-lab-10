# Spec: F1 · Chat y ciclo de una tarea

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §7, §8 P0 front, §14

## 1. Qué es y por qué
La pantalla principal: la persona escribe en lenguaje natural lo que necesita y ve el resultado. Es la feature vertical más corta de punta a punta: chat → `POST /tasks` → estado → resumen.

## 2. Decisiones firmes
- **Stack: por decidir** (ver abiertas). El reto no impone stack al front; la propuesta Next.js + Vercel viene del curso, no del reto. Cualquiera que elijan debe tener servidor propio para el proxy `/api/*`.
- **Estilos:** según `DESIGN-bepelican.md` (tokens y componentes `chat-bubble-agent`, `chat-bubble-human`, `button-*`), sin rediseñar. Montserrat para toda la UI funcional; Citadel Script no se usa aquí.
- **Servidor del front (`/api/*`):** reenvía al back agregando el `Bearer` y, en `POST /tasks`, el `escritorio` desde variables de entorno (contrato §2). El navegador no ve token ni contraseña.
- **Flujo:** la persona envía → el front crea la tarea con `canal:"chat"` → abre el SSE → muestra en el chat los mensajes de `paso` y, al llegar `fin`, el `resumen` como respuesta.
- **Una tarea activa por conversación.** Mientras `estado = en_curso`, el campo de texto queda deshabilitado con una nota.
- **Estados visibles:** enviando, en curso, en espera de ti, terminada, fallida. `fallida` se muestra como "no pude completarlo" con el resumen, nunca como error técnico.
- **Responsive:** funciona en móvil. El escritorio en vivo (F2) pasa a una pestaña en pantallas estrechas.
- **Resumen:** se muestra tal cual; no se interpreta ni se reformatea (puede traer la línea `respuesta:`).

## 3. Decisiones abiertas
- [ ] Framework y host del front. Candidato: Next.js + Vercel (curso). Lo decide quien construye el front (Dani); solo debe cumplir el proxy y el SSE.
- [ ] ¿Se guarda el historial del chat entre recargas? Propuesta P0: solo en `sessionStorage`; sin login no hay más.

## 4. Descartado
Login (P2). Hablar directo con el back desde el navegador (expondría el token). Lista de tareas anteriores.

## 5. Edge cases
- Recarga a mitad de tarea: al volver, si hay `task_id` en `sessionStorage`, se retoma el SSE con `Last-Event-ID`.
- Back caído o 401: mensaje "no pude conectar", sin detalles técnicos ni token.
- `POST /tasks` lento (> 2 s): el chat muestra "enviando" sin bloquear.

## 6. Fuera de scope
Telegram, adjuntos, voz, varios chats.

## 7. Referencias
`PRD.md` §7–§8 · `specs/00-contrato-back-front.md` · `DESIGN.md`

## Verificación
Contra el back real o el mock del contrato: enviar una tarea y ver pasos y resumen final. Recargar a mitad y comprobar que retoma sin duplicar mensajes. Revisar en 375 px de ancho.
