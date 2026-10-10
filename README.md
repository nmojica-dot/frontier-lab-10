# Agente que opera lo que no tiene API

Proyecto del **Reto 1** de Frontier BOG/26. Aquí está todo lo que sabemos, lo que decidimos y lo que falta.

## 0. La tesis
**Confiable antes que inteligente.** Navegante es un empleado digital que aprende a usar programas desconocidos, con reglas para no actuar sin control. Vale más que haga 7 tareas bien y reconozca que no puede con otras 3, que intentar 10 y equivocarse en silencio en 3. Lo que demostramos: autonomía + adaptación + precisión sobre una app que nadie programó para ella.

## 1. En una frase
Un servicio en internet que recibe una tarea en lenguaje normal ("Corrige la dirección del cliente X") y un acceso a un computador remoto, usa la aplicación vieja de ese computador por pantalla, como lo haría una persona, y devuelve un resumen honesto de lo que hizo.

## 2. La analogía: un mesero nuevo
Piensa en un mesero que llega a un restaurante que no conoce:

| En el restaurante | En nuestro proyecto |
|---|---|
| El cliente dice el pedido | Llega la tarea en lenguaje normal |
| El mesero ve el salón y el menú | El agente toma capturas de pantalla y las lee |
| El mesero decide qué hacer | Un modelo de IA (vía OpenRouter) decide el siguiente clic |
| El mesero camina, anota, sirve | Un programa manda clics y teclas al computador remoto |
| Si hay dos "Ana" en las mesas, pregunta | Si hay dos registros iguales, no cambia nada y reporta `fallida` con datos |
| Anota el pedido exacto antes de ir a la mesa y no sirve nada que no esté en la nota | Antes de mirar la app, fija un "contrato de cambios" sacado de la tarea y no cambia nada fuera de él |
| Si en la mesa hay un papel que dice "tráiganos postre gratis", no lo obedece | El texto que aparece dentro de la app es información, nunca una orden |
| Para leer un precio, mira la carta de cerca en vez de adivinar desde lejos | Para leer un dato, copia el texto de la pantalla (Ctrl+A, Ctrl+C) en vez de adivinarlo en la imagen |
| El segundo día ya sabe dónde queda la cocina | Recuerda el camino dentro de cada app para las tareas siguientes, y lo comprueba |
| Al final cuenta cómo salió todo | Devuelve `terminada` o `fallida` y un resumen verdadero |

Lo que más puntúa no es que el mesero sea rápido, sino que **no se equivoque en silencio**.

## 3. Cómo funciona, paso a paso
```
Evaluador ──► POST /tasks (tarea + acceso al escritorio)
                │  responde "recibido, task_id" en < 2 s
                ▼
          Worker de la tarea (máx. 4:30)
   1. Conectar    entra al escritorio, lee la fecha de "hoy" y recuerda la app si ya la conoce
   2. Contrato    anota qué se puede cambiar, sacado solo de la tarea
   3. Ciclo       mira la pantalla → el modelo elige una herramienta → el código revisa
                  que esté permitida → actúa → compara lo que esperaba con lo que pasó
   4. Verificar   relee el registro: ¿quedó bien?, ¿hay duplicados?
   5. Reportar    el código escribe el resumen (sin contraseñas) y se desconecta
                ▼
Evaluador ──► GET /tasks/{id} → { estado, resumen }
```
Diagrama completo: [systems-design/arquitectura.png](systems-design/arquitectura.png). Razonamiento completo, con lo que refutamos: [systems-design/bosquejo.md](systems-design/bosquejo.md).

Aclaración clave: la API que aparece arriba es la nuestra (la que exige el reto). El sistema viejo **no tiene API**: Navegante solo lo ve y lo opera por pantalla (RFB), con mouse y teclado.

## 4. Qué nos califican
| Parte | Peso | Cierra |
|---|---|---|
| Systems design (doc + diagrama) | 30 % | 12:00 |
| Ejecución (repo, servicio desplegado, video de 2 min, pruebas ocultas) | 40 % | 20:00 |
| Demo day (pitch) | 15 % | tu turno |
| Profundidad técnica (debrief de 10 min) | 15 % | después |

Una tarea está bien si: la app quedó con el cambio pedido y nada más, sin duplicados, con el `estado` correcto, y el resumen no filtra la contraseña. A las 15:30 la app cambia y puntúan si el agente se adapta.

## 5. Mapa de la carpeta
| Archivo | Para qué sirve |
|---|---|
| [README.md](README.md) | Este índice y la explicación sencilla |
| [CONTEXTO.md](CONTEXTO.md) | Nota técnica para retomar el trabajo en otra sesión: estado, reglas, decisiones y pendientes |
| [systems-design/diseno.md](systems-design/diseno.md) y `diseno.pdf` | **Entrega de las 12:00:** el doc de diseño de una página (se sube el PDF) |
| [systems-design/arquitectura.svg](systems-design/arquitectura.svg) y `arquitectura.png` | **Entrega de las 12:00:** el diagrama de arquitectura (se sube el PNG) |
| [systems-design/bosquejo.md](systems-design/bosquejo.md) | El razonamiento completo: qué refutamos, qué verificamos y qué falta probar |
| `systems-design/diseno-v1.md` | Versión anterior del doc, para comparar |
| [systems-design/prompt-lovable.md](systems-design/prompt-lovable.md) | Prompt en dos mensajes para que quien diseña arme la landing (el doc web de la entrega) en Lovable |
| `material-reto1/extraido/README.md` | El README oficial del reto (formato del resumen, reglas, evaluación) |
| `material-reto1/extraido/pruebas/` | Las 5 tareas de práctica E1–E5 con lo que se espera |

## 6. Las 5 tareas de práctica
| ID | Qué pide | Qué prueba |
|---|---|---|
| E1 | Registrar un cliente nuevo | Llenar un formulario sin errores ni duplicados |
| E2 | Corregir la dirección de un cliente | Encontrar el registro correcto y editar solo ese campo |
| E3 | Contar facturas vencidas de un cliente | Responder una pregunta con `respuesta: <número>` |
| E4 | Exportar el reporte de pedidos entregados de septiembre | Usar filtros por fecha y exportar |
| E5 | Cambiar el teléfono de "Ana Torres" | Hay dos: debe fallar y nombrar los dos documentos |

## 7. Lo que ya decidimos
- El agente habla con el escritorio por **RFB directo** (no abre un navegador intermedio).
- El **modelo con visión** se usa por **OpenRouter**. La llave va solo en una variable de entorno del servidor, nunca en el repo.
- Ante la duda, **falla con explicación** en vez de adivinar.
- Estado en memoria con SQLite de respaldo, sin infraestructura extra.
- El modelo **elige herramientas**; el **código** decide lo que debe ser exacto: fechas, conteos, formato de la respuesta y tiempos.
- **Contrato de cambios:** solo se escriben valores que salen de la tarea. Guardar, Exportar o Eliminar se pulsan solo si la tarea lo pide, y una sola vez.
- **Leer exacto:** cuando se pueda, se copia el texto de la pantalla en vez de adivinarlo en la imagen.
- **Memoria por app:** el camino aprendido se reusa en las tareas siguientes, comprobándolo cada vez.
- **Modelo:** Claude Sonnet 5.5 como principal contra Gemini 3.5 Flash Lite. Gana el que mejor salga en nuestras pruebas.

## 8. Lo que aprendimos de la app de práctica (SIGECOM)
- Los submenús abren con **hover**, no con clic.
- La búsqueda **distingue tildes** y hay nombres casi iguales.
- Las listas **paginan** y piden scroll.
- Tras cada clic hay que **esperar ~1 s** antes de capturar; los clics muy cortos se ignoran; al escribir hay que **limpiar el campo** antes.

## 9. Qué sigue
1. **Antes de las 12:00:** subir `diseno.pdf` y `arquitectura.png` (ya generados) y preguntar a staff lo de OpenRouter.
2. **Experimentos de arranque (≤ 20 min cada uno):**
   - X1: conectar y capturar.
   - X2: copiar y pegar con tildes.
   - X3: puntería y velocidad de los dos modelos.
3. **Hito 2:** E5 y E3 (solo leen), luego E1, E2 y E4 (escriben).
4. **Hito 3:** variantes, memoria por app y prueba del cambio de las 15:30.
5. **Antes de las 20:00:** desplegar, probar el contrato (`/health`, `POST /tasks`, `GET /tasks/{id}`) y grabar el video.

## 10. Glosario rápido
- **Entrypoint:** la URL pública de nuestro servicio, con las tres rutas del contrato.
- **RFB / VNC / noVNC:** el protocolo con el que se ve y se controla el computador remoto; noVNC es su versión en el navegador.
- **Agente:** el programa que repite ver, decidir, actuar y verificar hasta terminar.
- **Falso éxito:** reportar `terminada` cuando la app no quedó bien. Es el peor error.
- **Set oculto:** las pruebas de evaluación que corren sobre una app que no hemos visto.
