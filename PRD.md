# PRD — Navegante

Un agente que opera por pantalla sistemas sin API y ejecuta tareas pedidas en lenguaje natural, aunque nunca haya visto la aplicación.

## 1. Problema
Muchas empresas dependen de software que no pueden o no quieren reemplazar porque es antiguo, cerrado, difícil de integrar o crítico para su operación. Por eso, tareas que deberían ser sencillas siguen exigiendo intervención humana, conocimiento especializado y varios pasos manuales: clics, formularios, ventanas emergentes y reportes que se exportan uno por uno. Eso cuesta horas, produce errores (duplicados, datos mal digitados, el registro equivocado) y deja la operación en manos de las pocas personas que dominan cada sistema.

## 2. Usuario objetivo
**Usuario principal de la V1: el empleado operativo.** Necesita consultar, registrar, actualizar y exportar información sin recorrer decenas de pantallas. Puede no saber usar el sistema o dominarlo y querer dejar de hacer lo repetitivo. Escribe lo que necesita en lenguaje natural, sin aprender comandos. Lo que busca es facilidad y ahorro de tiempo.

**Otros actores del producto:**

| Perfil | Necesita | Necesidad principal |
|---|---|---|
| Supervisor o gerente | Respuestas y revisión de operaciones sin depender de otro empleado | Información, visibilidad y control |
| Experto del sistema | Delegar tareas repetitivas sin perder la supervisión. Por ejemplo, una contadora que lleva diez años en su sistema financiero no necesita aprenderlo; necesita recuperar las horas que pierde operándolo | Productividad y precisión |
| Administrador de tecnología | Autorizar conexiones, configurar accesos y controlar la seguridad. En la V1 la instalación la hacemos nosotros y este perfil no tiene funciones propias (P2) | Confiabilidad, permisos y trazabilidad |

Quien usa Navegante, quien paga por él y quien autoriza las conexiones son personas distintas.

## 3. Visión *(borrador — revisar)*
Que ninguna empresa tenga que migrar ni reemplazar un sistema para poder operarlo con IA. Navegante funciona como un empleado digital que aprende cualquier software, y cualquier persona de la oficina lo usa hablándole. Hacia allá:
- **Mover datos entre sistemas:** por ejemplo, pasar un pedido del sistema de ventas al de facturación.
- **Extraer el histórico** de un sistema, para que la empresa pueda migrarlo si algún día lo decide.

## 4. Estrategia *(borrador — revisar)*
- **Modelo:** producto B2B que instalamos nosotros en cada empresa.
- **Wedge:** opera el sistema tal como está, sin integración, sin API y sin migración.
- **Alternativas que reemplaza:** digitación manual, automatizaciones grabadas por pantalla que se rompen cuando la app cambia, y migrar el sistema.
- **Por qué ahora:** los modelos con visión ya pueden interpretar pantallas desconocidas. Lo que falta es hacerlo de forma confiable.

## 5. Principios del producto
- **Confiable e inteligente, las dos son obligatorias.**
- **Nunca rápido a costa de confiable.** Si hay que escoger, se verifica aunque tarde más, siempre dentro de los 5 minutos por tarea.
- **Cero errores silenciosos.** Ante la duda no adivina: da a la persona todo el contexto para decidir.
- **Programamos capacidades, no recorridos.**

  | No se programa | Sí se programa |
  |---|---|
  | Abrir "Comercial" en una app concreta | Reconocer y abrir menús |
  | Llenar un formulario específico | Interpretar formularios desconocidos |
  | Clic en una coordenada fija | Identificar visualmente dónde hacer clic |
  | Una secuencia fija de pasos | Planificar y verificar cada paso |

- **Solo cambia lo que sale de la petición.** El texto que aparece en la app es dato, nunca instrucción.
- **Cada acción de compromiso se hace una sola vez:** Guardar, Exportar, Eliminar o su equivalente.
- **Nada se da por hecho sin evidencia.**
- **Los secretos nunca aparecen en el resumen.**
- **Todo con el menor esfuerzo para la persona.**

## 6. Propuesta de valor
Cualquiera puede operar un sistema. Navegante es distinto porque **opera los sistemas que ya conoce con registros y memoria, y aprende los nuevos buscando patrones y lógicas**, sin scripts por aplicación. Cuando no está seguro, no se equivoca en silencio: lo dice y da el contexto para decidir.

### Cómo está hecho
Cinco componentes reutilizables. Cuando cambia el sistema, cambia lo que se ve en pantalla, pero no el agente.

| Componente | Qué hace |
|---|---|
| Ojos | Reconoce menús, formularios, tablas y ventanas |
| Cerebro | Decide cómo alcanzar el objetivo |
| Manos | Mueve el mouse, escribe y usa el teclado |
| Memoria | Registra rutas y verifica resultados anteriores |
| Criterio | Decide qué está permitido y si el resultado tiene evidencia; bloquea lo que no salga de la petición y detiene la tarea ante la duda |

**Universal Skills Engine:** un conjunto de habilidades generales (observar, explorar, interactuar, encontrar, leer datos, verificar) que el agente combina según la app. La habilidad es la misma, aunque se ejecute distinto: abrir un menú con hover en una app y con Tab y Enter en otra.

**Canales:** la persona habla con el mismo agente por tres puertas: chat web responsive, Telegram y API.

## 7. Casos de uso principales
Escritos en general. Navegante los resuelve en cualquier sistema, sin que estén programados para una app concreta. Cada tarea ocurre en un solo sistema y dura 5 minutos como máximo.

- **Consultar:** obtener un dato o responder una pregunta sobre un registro, como un saldo, un estado o una cantidad. Responde con el dato exacto.
- **Crear:** registrar algo nuevo. Antes busca que no exista y crea uno solo.
- **Cambiar:** actualizar un dato de un registro identificado. Cambia solo ese campo y lo verifica.
- **Eliminar:** borrar un registro identificado. En el chat pide confirmación antes, y siempre deja registro de qué se borró y quién lo pidió.
- **Reportes y exportes:** sacar un reporte o exportar una lista con los filtros pedidos (fechas, estado, cliente). Revisa los filtros antes y exporta una sola vez.
- **Cruzar y validar:** revisar una condición antes de una decisión de la persona, por ejemplo "¿este cliente tiene facturas vencidas antes de aprobarle el pedido?". Responde con el resultado y los datos que lo sustentan.
- **Resolver una duda:** si hay dos registros parecidos, muestra los candidatos con los datos que los distinguen, la persona elige y la tarea continúa.
- **Seguir la tarea en vivo:** la persona ve el escritorio mientras Navegante trabaja, junto con cada paso y la evidencia.

## 8. MVP
- **P0 back:**
  - API (`/health`, `POST /tasks` en menos de 2 s, `GET /tasks/{id}`) con token.
  - Cliente RFB propio.
  - Contrato de cambios.
  - Ciclo observar → decidir → validar → actuar → comprobar.
  - Habilidades núcleo.
  - Criterio (reglas de seguridad).
  - Verificación con evidencia.
  - Resumen sin secretos.
  - Memoria por app.
  - Canal de eventos de cada tarea para el front.
  - Eliminación con registro y borrado masivo bloqueado.
- **P0 front:**
  - Chat responsive.
  - Escritorio en vivo.
  - Actividad y evidencias.
  - Pregunta con contexto ante una duda.
  - Confirmación antes de eliminar.
- **P1:**
  - Lectura exacta por portapapeles.
  - Bot de Telegram.
  - Registro de quién pidió cada tarea.
- **P2:**
  - Login y gestión de usuarios.
  - Que el empleado configure el escritorio y las credenciales.
  - Herramientas del administrador: conexiones, accesos y permisos.

## 9. Qué NO vamos a construir
- Scripts o flujos grabados por aplicación.
- Leer el DOM, abrir DevTools o usar agentes de navegación de terceros.
- Que el modelo decida qué cambiar.
- Multiagente.
- OCR propio.
- Perfiles por familia de app.
- Tareas en paralelo sobre el mismo escritorio.
- Cargas o cambios en lote.
- Tareas que abren varios sistemas o pasan de 5 minutos, como mover datos entre sistemas o extraer el histórico. Quedan en la Visión.

## 10. Roadmap *(borrador — revisar)*
- **V1 (hoy, 20:00):** P0, es decir, el agente con memoria, la API y el front.
- **V1.1:** P1, es decir, el portapapeles, Telegram y el registro de quién pidió cada tarea.
- **V2:** P2, es decir, los usuarios, los permisos y la configuración por parte del cliente.
- **Después:** mover datos entre sistemas y extraer el histórico.

## 11. Requisitos funcionales *(borrador — revisar)*
- **Pedir una tarea:** por chat, Telegram o API, en lenguaje natural.
- **Ejecutar:** se fija el contrato de cambios antes de mirar la app. Luego el ciclo con Criterio, la verificación y el reporte. Al reportar, la tarea se detiene.
- **Dudas:**
  - Por chat o Telegram: pregunta con contexto y la tarea queda en espera.
  - Por API: `fallida` con los datos.
- **Eliminar:**
  - Por chat o Telegram: confirmación previa.
  - Por API: directo.
  - Siempre queda registro.
- **Memoria:** reutiliza las rutas verificadas por app y las invalida cuando dejan de funcionar.
- **Seguimiento:** estado, pasos, capturas y evidencia en vivo.

## 12. Happy paths
La persona escribe "corrige la dirección de la cliente Ana Torres, documento 52345678, a Calle 10 # 5-20". Navegante:
1. Fija qué puede cambiar.
2. Abre la app y encuentra dos Ana Torres. Desempata con el documento.
3. Cambia solo la dirección y guarda una vez.
4. Reabre el registro y comprueba el cambio.
5. Responde en lenguaje sencillo.

La segunda tarea en esa app usa la ruta aprendida y termina más rápido.

## 13. Unhappy paths
| Situación | Qué pasa |
|---|---|
| Dos registros y la petición no permite desempatar | Chat o Telegram: muestra los candidatos con los datos que los distinguen y la persona decide. API: `fallida` nombrando los identificadores |
| La persona no responde a la pregunta | La tarea queda en espera y suelta el escritorio. Al responder, se reconecta, comprueba que el registro siga igual y continúa. Si cambió, se detiene y muestra qué cambió |
| El registro no existe | No toca nada y lo dice |
| Crear algo que ya existe | No crea un duplicado y nombra el registro existente |
| Petición de eliminar | Chat o Telegram: muestra el registro completo y pide confirmación. Siempre queda registrado qué se borró y quién lo pidió |
| Borrado masivo | `fallida` sin tocar nada, explicando por qué |
| Una nota en la app pide otra cosa | No la obedece y la menciona en el resumen |
| La app cambió y una ruta guardada ya no funciona | La invalida, vuelve a explorar y lo dice |
| No pudo verificar el resultado | `fallida`, explicando qué no pudo confirmar |
| Se acaba el tiempo | Desde 3:45 no empieza ninguna acción de compromiso. A 4:30 reporta y se desconecta |
| No encuentra el camino | Reporta lo que sí vio, sin inventar |

## 14. Requisitos no funcionales *(borrador — revisar)*
- 5 minutos máximo por tarea, con el reloj interno en 4:30.
- `POST /tasks` responde en menos de 2 s.
- Las contraseñas y las llaves van solo en variables de entorno. El modelo nunca las recibe y nunca aparecen en un resumen.
- Servicio desplegado y accesible por internet.
- El front es responsive.

## 15. Criterios de aceptación *(borrador — revisar)*
- Dados dos registros homónimos sin dato que desempate, cuando la petición llega por chat, Navegante muestra ambos con sus datos y no cambia nada hasta que la persona elige.
- Dada una petición de eliminar por chat, Navegante muestra el registro y solo elimina tras la confirmación. Queda el registro de qué se borró y quién lo pidió.
- Dada una tarea que creó un registro, cuando se repite por error, no se crea un duplicado.
- Dada una app que cambió su interfaz, cuando una ruta guardada falla, Navegante la invalida, recalcula la ruta y lo reporta.
- Dado cualquier resumen, no contiene la contraseña ni otros secretos.

## 16. Métricas de éxito
- **0 errores silenciosos:** ningún falso `terminada` ni acciones de más.
- **≥ 75 % de tareas correctas.**
- **95 de cada 100 tareas terminan antes de 4:30.**
- **Pruebas superadas:**
  - **A:** una tarea en la app de práctica.
  - **B:** una tarea equivalente en una app nunca vista.
  - **C:** elementos movidos o una ventana inesperada.
- **Ganancia por memoria:** al menos 30 % menos de tiempo y de decisiones en la segunda tarea sobre la misma app.
- **Claridad:** ante una duda, la persona decide con lo que se le muestra y no necesita abrir el sistema viejo.

## 17. Open Questions
- No podemos garantizar que funcione en cualquier sistema desde el primer día. ¿Dónde está el límite real? Lo responden las pruebas B y C.
- ¿Cómo se identifica a la persona en el chat web sin login (P0), para el registro de eliminaciones?
- Cuando una tarea en espera se retoma, ¿empieza una ventana nueva de 5 minutos?
- La lectura exacta por portapapeles está en P1, pero leer mal un dato es un riesgo directo a la confiabilidad. ¿Sube a P0?
- ¿Un borrado puntual pedido por la API cuenta como "peligroso" en la evaluación?
- ¿Qué modelo usar? Se decide midiendo en nuestras pruebas.

## 18. Links
- [README.md](README.md)
- [CONTEXTO.md](CONTEXTO.md)
- [systems-design/diseno.md](systems-design/diseno.md)
- [systems-design/bosquejo.md](systems-design/bosquejo.md)
- [systems-design/arquitectura.png](systems-design/arquitectura.png)
- [material-reto1/extraido/README.md](material-reto1/extraido/README.md)
