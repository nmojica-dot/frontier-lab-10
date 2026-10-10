# Spec: B5 · Memoria por app

> Estado: en exploración (entra después del núcleo)
> Última actualización: 2026-10-10 · PRD: §6, §11, §16

## 1. Qué es y por qué
Guarda lo que el agente aprendió de una app (rutas verificadas, perfil de interacción) para que la segunda tarea sea más rápida. Meta: ≥ 30 % menos de tiempo y de decisiones.

## 2. Decisiones firmes
- **Clave de app:** huella de la pantalla (título de ventana + estructura de menús) leída al conectar.
- **Qué se guarda:** rutas de navegación (`ir_a`), perfil de interacción (ej. menús abren con hover) y si fueron verificadas.
- **Cuándo se guarda:** solo rutas que llevaron a un resultado verificado (B4).
- **Invalidación:** si una ruta guardada no da lo esperado, se invalida, se vuelve a explorar y el resumen lo dice.
- **Almacén:** SQLite, tabla por app.
- **Sin datos de negocio:** no se guardan nombres, documentos ni valores de registros.

## 3. Decisiones abiertas
- [ ] ¿La memoria sobrevive a un escritorio "limpio y distinto"? Se asume que la huella cambia y se parte de cero; se mide con la prueba C.

## 4. Descartado
Scripts o flujos grabados por app. Perfiles por familia de app.

## 5. Edge cases
Dos apps con la misma huella. App que cambia a mitad del día (incidente de las 15:30): la ruta falla → invalidar.

## 6. Fuera de scope
Compartir memoria entre clientes.

## 7. Referencias
`PRD.md` §6, §16 · `systems-design/bosquejo.md`

## Verificación
Misma tarea dos veces en SIGECOM: la segunda con ≥ 30 % menos decisiones. Mover un elemento de lugar: la ruta se invalida y el resumen lo menciona.
