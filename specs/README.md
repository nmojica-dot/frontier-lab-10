# Specs de Navegante

Siguen el paso 4 del curso (Spec-Driven Development): **conversación → spec → código de una feature → verificar**. Una spec por feature, en vertical (pantalla, lógica y datos de punta a punta), en el repo y versionada.

Documentos que van antes de las specs: `PRD.md` (hecho) · `DESIGN-bepelican.md` (el de BePelican, ya lo tiene Dani) · `CLAUDE.md` (pendiente).

## Índice

| Spec | Frente | Qué construye | Depende de |
|---|---|---|---|
| [00 Contrato](00-contrato-back-front.md) | ambos | Endpoints, eventos SSE, errores | PRD |
| [B1 API de tareas](back/B1-api-tareas.md) | back | `/health`, `POST /tasks`, `GET /tasks/{id}` | 00 |
| [B2 Cliente RFB](back/B2-cliente-rfb.md) | back | Conectar, capturar, mouse y teclado | — |
| [B3 Ciclo del agente](back/B3-ciclo-agente.md) | back | Contrato de cambios, ciclo, herramientas núcleo | B1, B2 |
| [B4 Criterio y verificación](back/B4-criterio-verificacion.md) | back | Reglas de seguridad, evidencia, resumen sin secretos | B3 |
| [B6 Canal de eventos y espera](back/B6-canal-eventos-y-espera.md) | back | SSE, preguntas, pantalla, capturas | B1, B3 |
| [B5 Memoria por app](back/B5-memoria-por-app.md) | back | Rutas aprendidas e invalidación | B3, B4 |
| [F1 Chat y tarea](front/F1-chat-y-tarea.md) | front | Chat, servidor proxy, estados | 00 |
| [F2 Escritorio en vivo](front/F2-escritorio-en-vivo.md) | front | Cuadros del escritorio | F1 |
| [F3 Actividad y evidencias](front/F3-actividad-y-evidencias.md) | front | Línea de tiempo con capturas | F1 |
| [F4 Preguntas y confirmación](front/F4-preguntas-y-confirmacion.md) | front | Elegir candidato, confirmar eliminar | F1, F3 |

## Plantilla (copiar para cada spec nueva)

```
# Spec: [Nombre]
> Estado: en exploración | decidido | en construcción | construido
> Última actualización · PRD relacionado

1. Qué es y por qué (1–2 frases)
2. Decisiones firmes (flujo, UI/estados, contratos y datos)
3. Decisiones abiertas (checklist)
4. Descartado (y por qué)
5. Edge cases
6. Fuera de scope
7. Referencias
Verificación (cómo se comprueba, con evidencia)
```

Una spec pasa a `decidido` cuando no le quedan abiertas que bloqueen. Al terminar la feature pasa a `construido` en el mismo commit.

---

# Proceso de trabajo

## Reglas
1. **El contrato manda.** Cualquier cambio entre back y front se hace primero en `00-contrato-back-front.md`, se avisa al otro frente y luego se codifica.
2. **Una feature a la vez por frente**, completa y verificada, con commit antes de la siguiente.
3. **Sin diseño nuevo.** El front usa `DESIGN.md` y sus componentes; si falta uno, se pide en la spec, no se inventa.
4. **El PRD es el límite.** Lo que no está en P0 no se construye. Si aparece algo, va a "fuera de scope" de la spec.
5. **Evidencia, no promesas.** Cada spec cierra con su Verificación ejecutada y mostrada.
6. **Secretos fuera del repo** (repo público): `.env` en `.gitignore`, `.env.example` sin valores. La contraseña del escritorio la carga una persona en su terminal.

## Prioridad por peso en el reto
Rúbrica: Ejecución 40 % (solo la API contra apps ocultas, cierra 20:00), Systems design 30 % (ya entregado), Demo day 15 %, Profundidad técnica 15 % (debrief individual: cada quien debe poder explicar lo que construyó).

Por eso el orden de construcción, cuando haya que escoger, es:
1. **B1 → B2 → B3 → B4:** lo único que se evalúa automáticamente. Cero errores silenciosos antes que nada.
2. **Despliegue de la API** y prueba del contrato con token (no se deja para el final).
3. **B6 + F1 + F4:** lo mínimo del front para la demo: pedir tarea, ver el estado, resolver duda y confirmar eliminar.
4. **B5 (memoria):** pesa en el incidente de las 15:30 (la app cambia y la ruta se invalida).
5. **F2 + F3:** escritorio en vivo y evidencias. Primero en recortarse si falta tiempo; el video puede mostrar el escritorio por otra vía.

Corte: si a las 16:30 el éxito del back es < 50 % o hay un falso éxito sin explicar, el front se congela y todos refuerzan verificación (regla de `systems-design/diseno.md` §3).

## Fases

**Fase 0: preparar (una vez)**
- Crear el repo con `back/`, `front/`, `specs/`, `docs/PRD.md` y `DESIGN.md` en la raíz.
- `CLAUDE.md` por frente (`back/CLAUDE.md`, `front/CLAUDE.md`) y uno corto en la raíz. Cada uno bajo 300 líneas: stack, comandos exactos, convenciones, reglas con su reemplazo.
- Un worktree por frente (`git worktree add ../navegante-front front`) y una sesión de Claude Code por worktree en CMUX.
- Revisar las decisiones abiertas del contrato entre las dos personas y pasarlo a `decidido`.

**Fase 1: esqueleto en paralelo**
- **Back:** B1 con un worker de mentira que emite eventos del contrato. Desplegar en Railway ya.
- **Front:** F1 contra un mock del contrato (un servidor local con los mismos endpoints y eventos grabados). Desplegar en Vercel ya.
- Primera integración: el front real contra el back de mentira. Si no encaja, se corrige el contrato.

**Fase 2: el agente (back) y las vistas (front)**
- **Back:** B2 → B3 → B4 con los escenarios E5 y E3 primero (lectura), luego E1, E2, E4 (escritura). B6 en cuanto B3 emita pasos reales.
- **Front:** F2 → F3 → F4, cada una probada contra el mock y luego contra el back real.
- Cada feature: `spec → plan (pedir a Claude explorar y proponer 2–3 enfoques) → implementar → verificar → commit`.

**Fase 3: integración y robustez**
- Back real + front real sobre SIGECOM. Flujos: tarea simple, duda (E5), eliminar con confirmación, espera y retomar, caída de red.
- B5 (memoria) cuando el núcleo sea estable. Medir la ganancia de la segunda tarea.
- Pruebas A, B, C del PRD §16 y las metas: 0 errores silenciosos, ≥ 75 % correctas, p95 < 4:30.
- Revisión de seguridad: buscar la contraseña en logs, eventos, resúmenes y repo.

**Fase 4: entrega**
- Repo público limpio, entrypoint desplegado y probado con token, video de ≤ 2 min.
- README con cómo correr y cómo se verifica.

## Ciclo de cada feature con Claude Code
1. `/clear` y abrir con `@specs/...` y `@PRD.md`.
2. "Lee la spec, explora el repo y proponme un plan. No escribas código." → revisar.
3. "Dame qué puede romper y los supuestos." → ajustar la spec si hace falta.
4. Implementar. Pedir evidencia (tests, salida, captura), no solo "listo".
5. Si una corrección falla dos veces: `/clear` y reescribir el prompt.
6. Verificación de la spec, commit pequeño con la spec actualizada a `construido`.

## Decisiones que necesitamos
Ver las casillas abiertas de cada spec. Las que bloquean ya: framework y host del front (el reto no lo impone; Next.js + Vercel es solo la sugerencia del curso) y las dos preguntas del contrato (identidad del solicitante y reloj al retomar).

Lo que sí impone el reto: servicio desplegado con las tres rutas, repo público, llaves solo en variables de entorno, video de ≤ 2 min, y no usar DOM, DevTools ni agentes de navegación de terceros. El front es parte de la demo, no de la evaluación automática.
