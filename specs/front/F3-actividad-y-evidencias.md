# Spec: F3 · Actividad y evidencias

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §5 "Nada se da por hecho sin evidencia", §7, §8 P0 front

## 1. Qué es y por qué
Una línea de tiempo de lo que hizo Navegante, con la evidencia que respalda cada resultado. Es lo que permite a la persona confiar sin abrir el sistema viejo.

## 2. Decisiones firmes
- **Fuente:** eventos SSE `paso` y `evidencia` (contrato §2). Se pintan en orden de `id`.
- **Cada paso:** número, texto y, si trae `captura`, una miniatura (`/capturas/{n}.jpg`) que abre en grande.
- **Evidencia:** se distingue visualmente de un paso (marca de verificado) y siempre muestra su captura.
- **Mismo hilo que el chat:** en escritorio de pantalla va en un panel lateral; en móvil, como pestaña.
- **Al terminar:** la línea de tiempo queda visible y el último elemento es el `resumen`.
- **Texto como dato:** todo texto que viene del back se muestra como texto plano, nunca como HTML.
- **Sin secretos:** el front no filtra nada; confía en que el back ya los quitó. Nunca muestra el cuerpo enviado en `POST /tasks` (lleva la contraseña del escritorio).

## 3. Decisiones abiertas
- [ ] ¿Mostrar el costo y el número de decisiones del modelo? Útil para la demo, no es P0.

## 4. Descartado
Mostrar el razonamiento interno del modelo. Editar o borrar pasos.

## 5. Edge cases
Capturas que fallan al cargar: se muestra el texto sin miniatura. Eventos repetidos tras reconectar: se descartan por `id`. Muchos pasos: lista con scroll interno, el último siempre visible.

## 6. Fuera de scope
Exportar la actividad, filtros, historial entre tareas.

## 7. Referencias
`specs/00-contrato-back-front.md` · `DESIGN.md`

## Verificación
Con una tarea de prueba: pasos en orden, evidencias con captura, sin duplicados tras forzar una reconexión del SSE.
