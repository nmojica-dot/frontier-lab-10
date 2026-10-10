# Spec: B3 · Ciclo del agente y habilidades núcleo

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §5, §6, §7, §12

## 1. Qué es y por qué
El worker que convierte una petición en lenguaje natural en acciones sobre una app desconocida. Ciclo: observar → decidir → validar → actuar → comprobar. "Programamos capacidades, no recorridos".

## 2. Decisiones firmes
- **Contrato de cambios** antes de mirar la app, a partir de la instrucción: registro objetivo, valores exactos a escribir, pregunta a responder y verbos de compromiso permitidos. Todo valor que se escriba debe salir de ahí (B4 lo exige).
- **Ciclo:** el modelo elige la herramienta y qué espera ver; el código valida (B4), ejecuta (B2) y compara esperado vs. real.
- **Modelo:** vía OpenRouter, salida JSON con esquema, proveedor fijo. Se mide Claude Sonnet 5.5 contra Gemini 3.5 Flash Lite (X3); Haiku 5.5 de respaldo. Meta: ≤ 15 decisiones del modelo por tarea.
- **Herramientas núcleo** (en este orden de construcción): `ver`, `clic`/`hover`/`tecla`, `buscar_registro` (con y sin tilde, cuenta candidatos), `llenar_campos` (teclear y releer), `leer_tabla` (todas las páginas), `fechas`, `confirmar` (Guardar o Exportar, una sola vez), `terminar`/`fallar`.
- **Verbos de compromiso** (Guardar, Exportar, Eliminar): una sola vez, nunca se reintentan a ciegas.
- **Reloj:** desde 3:45 no empieza ningún compromiso; a 4:30 reporta y cierra. La espera por una persona pausa el reloj (ver contrato, decisión abierta).
- **Eventos:** cada paso emite `paso`, cada comprobación `evidencia` (contrato §2).
- **Costo:** se registra por tarea; al pasar el tope se corta con `fallida`.

## 3. Decisiones abiertas
- [ ] Modelo final (se decide con E1–E5, X3).
- [ ] Texto exacto por portapapeles (`leer_texto`): P1, pero ver riesgo en PRD §17.

## 4. Descartado
Una llamada al modelo por clic (no cabe en 4:30). Que el modelo decida qué cambiar. Scripts o rutas fijas por app.

## 5. Edge cases
Los del PRD §13: homónimos, registro inexistente, duplicado, nota en la app que da órdenes (es dato, se menciona en el resumen), ventana inesperada, ruta guardada que ya no funciona, sin camino.

## 6. Fuera de scope
Multiagente, OCR propio, tareas sobre varios sistemas, lotes.

## 7. Referencias
`PRD.md` §5–§7, §12–§13 · `systems-design/diseno.md` §2

## Verificación
Tareas E1–E5 de `material-reto1/extraido/pruebas/` con `/__reset` y `/__check`, 3 corridas cada una. Orden: E5 y E3 (lectura) antes que las de escritura.
