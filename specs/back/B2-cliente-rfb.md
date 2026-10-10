# Spec: B2 · Cliente RFB y captura

> Estado: en exploración (es el experimento X1/X2 de CONTEXTO.md)
> Última actualización: 2026-10-10 · PRD: §8 P0 back

## 1. Qué es y por qué
Cliente propio del protocolo RFB sobre `wss://.../websockify`. Da al agente ojos (captura) y manos (mouse, teclado). Sin esto no hay agente.

## 2. Decisiones firmes
- **Conexión:** websocket con subprotocolo `binary`, RFB 003.008, seguridad tipo 2 (VNC auth). Pantalla 1280×800.
- **API interna mínima:** `conectar()`, `capturar() -> imagen`, `mover(x,y)`, `clic(x,y)`, `doble_clic`, `hover(x,y)`, `teclear(texto)`, `tecla(nombre)`, `cerrar()`.
- **Esperas:** tras cada acción se espera ~1 s antes de capturar (la pantalla tarda en repintar).
- **Clic:** mantener pulsado > 100 ms entre bajar y soltar, o se ignora.
- **Teclear sobre un campo con texto:** el llamador selecciona todo antes; el cliente no lo hace solo.
- **Último cuadro:** cada captura se guarda como el "último cuadro" que sirve `pantalla.jpg` (JPEG calidad ~60).
- **Cierre:** tras `fin` o a los 5 min, `cerrar()` y no se vuelve a actuar.

## 3. Decisiones abiertas
- [ ] ¿Librería RFB existente o implementación propia? Probar primero una existente; propia solo si falla (X1).
- [ ] ¿El portapapeles (cut text) viaja por RFB? Se prueba en X2; si no, el modelo lee recortes. Es P1 pero el PRD lo cuestiona (§17).

## 4. Descartado
Navegador sin interfaz y DOM/DevTools: lo prohíbe el reto.

## 5. Edge cases
- Caída del websocket a mitad de tarea: un reintento de reconexión; si falla → `fallida` ("se perdió la conexión con el escritorio").
- Autenticación rechazada: `fallida` sin exponer la contraseña.
- Captura idéntica a la anterior tras una acción: se reporta al ciclo (B3) como "sin cambio", no se asume éxito.

## 6. Fuera de scope
Audio, transferencia de archivos, múltiples monitores.

## 7. Referencias
`CONTEXTO.md` "Trampas del escritorio" · `systems-design/bosquejo.md`

## Verificación
Script que conecta, guarda una captura 1280×800, hace un clic y una tecla, y vuelve a capturar. Una persona revisa la captura (X1).
