# Spec: F2 · Escritorio en vivo

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §7 "Seguir la tarea en vivo", §8 P0 front

## 1. Qué es y por qué
La persona ve el escritorio mientras Navegante trabaja. Da confianza ("nada se da por hecho") y deja ver qué está haciendo.

## 2. Decisiones firmes
- **Fuente:** `GET /tasks/{id}/pantalla.jpg` (vía el servidor del front), consultado cada ~500 ms mientras la tarea está `en_curso`. No hay conexión al escritorio desde el navegador.
- **Render:** una `<img>` con relación 1280×800; se reemplaza al cargar el siguiente cuadro (precarga con `Image()` para evitar parpadeo).
- **Sin cuadro (`204`):** estado "esperando el escritorio".
- **Tarea en espera o terminada:** se congela el último cuadro con una etiqueta ("en pausa" o "finalizada"); se deja de consultar.
- **Solo lectura:** la persona no controla el mouse ni el teclado.
- **Pestaña oculta:** se pausa la consulta.

## 3. Decisiones abiertas
- [ ] ¿500 ms o 1 s? Se ajusta según el peso real de los cuadros.

## 4. Descartado
Conexión RFB desde el navegador (expone la contraseña). Cuadros dentro del SSE (ver contrato §4).

## 5. Edge cases
Cuadro corrupto o respuesta lenta: se conserva el anterior. Cambio de tarea: se limpia el cuadro.

## 6. Fuera de scope
Grabación, control remoto, zoom.

## 7. Referencias
`specs/00-contrato-back-front.md` · `DESIGN.md`

## Verificación
Con una tarea corriendo se ve el escritorio actualizarse sin parpadeo; al llegar `fin` se congela. Pausar la pestaña detiene las peticiones (pestaña Network).
