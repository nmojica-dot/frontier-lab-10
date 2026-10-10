# Spec: B4 · Criterio, verificación y resumen

> Estado: en exploración
> Última actualización: 2026-10-10 · PRD: §5, §13, §15

## 1. Qué es y por qué
La capa que decide qué está permitido y si hay evidencia. Es lo que hace cumplir "cero errores silenciosos". Es código, no modelo.

## 2. Decisiones firmes
- **Criterio (validar antes de actuar):**
  - Leer y navegar: libre.
  - Escribir: solo valores del contrato de cambios (literal de la instrucción, opción de lista que le corresponde o valor calculado).
  - Comprometer (Guardar, Exportar, Eliminar): exige un registro único verificado y que el verbo esté permitido.
  - Borrado masivo: bloqueado → `fallida` sin tocar nada.
  - Texto de la app = dato, nunca instrucción. Si pide algo, no se obedece y se menciona en el resumen.
- **Desempate:** solo con datos de la instrucción. Si no alcanzan: por chat → evento `pregunta` con candidatos; por API → `fallida` nombrando los identificadores.
- **Eliminar:** por chat → evento `confirmacion` con el registro completo; por API → directo. Siempre queda registro (qué se borró, quién lo pidió) en SQLite.
- **Verificación con evidencia independiente:** reabrir el registro, contar duplicados, revisar filtros antes de exportar. Sin evidencia → `fallida` explicando qué no pudo confirmar.
- **Resumen:** lo arma el código. Borra la contraseña y cualquier secreto conocido (la del escritorio, el token, las llaves) antes de guardarlo y de emitirlo. Lenguaje sencillo.
- **Respuestas con dato:** línea `respuesta: <valor>`, número primero, sin separador de miles; dos datos separados por `;`. Pregunta sin respuesta posible: sin esa línea.

## 3. Decisiones abiertas
- [ ] ¿Un borrado puntual por API cuenta como "peligroso" en la evaluación? (pregunta a staff, PRD §17).
- [ ] Formato numérico exacto de `respuesta:` (pregunta a staff).

## 4. Descartado
Elegir el candidato "más probable". Dejar que el modelo redacte el resumen sin filtro.

## 5. Edge cases
- Crear algo que ya existe: no duplica, nombra el existente.
- Registro cambió mientras la tarea esperaba: se detiene y muestra qué cambió.
- Secreto visible en una captura (pantalla de login con la contraseña escrita): las capturas no se filtran por píxeles, así que la contraseña se teclea sin capturar mientras está visible.

## 6. Fuera de scope
Permisos por usuario, aprobaciones de varios niveles.

## 7. Referencias
`PRD.md` §5, §13, §15 · `CONTEXTO.md` "Reglas de evaluación"

## Verificación
Los cinco criterios de aceptación del PRD §15 como pruebas automáticas, incluida una que busca la contraseña de prueba en todos los resúmenes y eventos.
