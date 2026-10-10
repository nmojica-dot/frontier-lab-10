# Spec: Contrato back ↔ front

> Estado: decidido (propuesto, falta visto bueno de ambos frentes)
> Última actualización: 2026-10-10 · PRD: §8 (P0), §11, §13

Es el único punto donde los dos frentes se tocan. Si cambia, cambia aquí primero.

## 1. Qué es y por qué
La API del reto (`/health`, `POST /tasks`, `GET /tasks/{id}`) más lo que el front necesita para mostrar la tarea en vivo: eventos, pantalla, y respuestas a preguntas. El front nunca habla con el escritorio ni ve secretos.

## 2. Decisiones firmes

**Autenticación.** Todo con `Authorization: Bearer <token del equipo>`. El navegador nunca ve el token: el front tiene un servidor propio (rutas `/api/*`) que reenvía al back y agrega el header. Por eso el front también guarda `ESCRITORIO_URL` y `ESCRITORIO_PASSWORD` en variables de entorno del servidor y los inyecta en `POST /tasks` (en P0 el chat no configura escritorio).

**Endpoints**

| Método y ruta | Cuerpo / respuesta |
|---|---|
| `GET /health` | `200 {"ok": true}` |
| `POST /tasks` | `{tarea, escritorio:{url,password}, canal?:"api"\|"chat", solicitante?}` → `{task_id}` en < 2 s. `canal` por defecto `api` |
| `GET /tasks/{id}` | `{estado:"en_curso"\|"terminada"\|"fallida", resumen, subestado?, pregunta?}` |
| `GET /tasks/{id}/eventos` | SSE. Soporta `Last-Event-ID` para reconectar sin perder eventos |
| `GET /tasks/{id}/pantalla.jpg` | Último cuadro del escritorio (JPEG). El front lo consulta cada ~500 ms |
| `GET /tasks/{id}/capturas/{n}.jpg` | Captura n de un paso, para la evidencia |
| `POST /tasks/{id}/respuesta` | `{pregunta_id, tipo:"eleccion"\|"confirmacion", valor}` → `202` |

`estado` solo toma los tres valores que exige el reto. La espera por la persona es `estado:"en_curso"` con `subestado:"en_espera"` y `pregunta` presente. Así el evaluador nunca ve un estado desconocido.

**Eventos SSE** (cada uno con `id` incremental por tarea; `data` es JSON)

| `event` | `data` |
|---|---|
| `estado` | `{estado, subestado?}` |
| `paso` | `{n, texto, captura?}` — texto en lenguaje sencillo, sin secretos |
| `evidencia` | `{n, texto, captura}` — lo que comprueba que algo quedó como se pidió |
| `pregunta` | `{pregunta_id, tipo:"eleccion", texto, candidatos:[{id, datos:{campo:valor}}]}` |
| `confirmacion` | `{pregunta_id, tipo:"confirmacion", accion:"eliminar", registro:{campo:valor}}` |
| `fin` | `{estado:"terminada"\|"fallida", resumen}` — último evento; el back cierra el stream |

Valor de `eleccion` = `id` del candidato; valor de `confirmacion` = `true` o `false`.

**Resumen.** Lo arma el back y ya viene sin secretos. El front lo muestra tal cual y no lo procesa.

**Errores.** Cuerpo `{error:{codigo, mensaje}}`. Códigos: `no_autorizado` (401), `tarea_no_existe` (404), `pregunta_no_vigente` (409), `entrada_invalida` (422).

## 3. Decisiones abiertas
- [ ] ¿Cómo identificar a la persona del chat para el registro de eliminaciones? Propuesta P0: el front manda `solicitante` (texto libre, "chat-web"). Pendiente por PRD §17.
- [ ] ¿Una tarea retomada abre ventana nueva de 5 minutos? (PRD §17). Hasta decidir: no, el reloj sigue y la espera lo pausa.

## 4. Descartado
- **Front conectado directo al escritorio (RFB/websockify):** exigiría la contraseña en el navegador.
- **Cuadros de pantalla dentro del SSE:** infla el stream y complica la reconexión. Mejor un endpoint de último cuadro.
- **Estado `en_espera` público:** rompe el contrato del evaluador.
- **WebSocket:** SSE basta (el front solo escucha; responde por POST).

## 5. Edge cases
- Reconexión del SSE a mitad de tarea: se reenvían los eventos desde `Last-Event-ID`.
- Tarea ya terminada al abrir el stream: se envían todos los eventos guardados y `fin`.
- Respuesta a una pregunta vencida o repetida: `409 pregunta_no_vigente`, sin efecto.
- `pantalla.jpg` sin cuadro aún: `204`.

## 6. Fuera de scope
Login y usuarios, configuración del escritorio por la persona, lista histórica de tareas (P2).

## 7. Referencias
`PRD.md` §8, §11, §13 · `systems-design/diseno.md` §2
