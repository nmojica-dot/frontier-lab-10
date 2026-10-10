"""Estado final de la tarea. `terminada` solo con evidencia; ante la duda, `fallida`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.criterio.contrato import ContratoCambios, Verbo


class Evidencia(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    descripcion: str
    confirmada: bool
    # Tomada después del compromiso (reabrir el registro, contar duplicados...).
    posterior_a_compromiso: bool = False


class EntradaEstado(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contrato: ContratoCambios
    evidencias: tuple[Evidencia, ...] = ()
    compromisos: tuple[Verbo, ...] = ()
    bloqueos: tuple[str, ...] = ()
    no_confirmado: tuple[str, ...] = ()
    respuesta: tuple[str | int | float, ...] = ()
    sin_respuesta_posible: bool = False
    # Texto que justifica que una tarea de escritura no necesitó compromiso
    # (p. ej. "el registro ya tenía ese valor").
    sin_cambios_justificados: str | None = None
    tiempo_agotado: bool = False
    tope_costo_excedido: bool = False
    error: str | None = None


class ResultadoEstado(BaseModel):
    model_config = ConfigDict(frozen=True)

    estado: Literal["terminada", "fallida"]
    motivos: tuple[str, ...] = ()


def decidir_estado(e: EntradaEstado) -> ResultadoEstado:
    motivos: list[str] = list(e.bloqueos)
    if e.error:
        motivos.append(f"Error: {e.error}")
    if e.tiempo_agotado:
        motivos.append("Se acabó el tiempo.")
    if e.tope_costo_excedido:
        motivos.append("Se pasó el tope de costo.")
    motivos += [f"No se pudo confirmar: {n}" for n in e.no_confirmado]

    if not e.evidencias:
        motivos.append("No hay evidencia de lo que pasó.")
    motivos += [
        f"Evidencia sin confirmar: {v.descripcion}" for v in e.evidencias if not v.confirmada
    ]

    fuera = [v for v in e.compromisos if v not in e.contrato.verbos_permitidos]
    if fuera:
        motivos.append(f"Se hizo algo que la instrucción no permitía: {', '.join(fuera)}.")
    if len(set(e.compromisos)) != len(e.compromisos):
        motivos.append("Un compromiso se ejecutó más de una vez.")

    if e.compromisos and not any(v.confirmada and v.posterior_a_compromiso for v in e.evidencias):
        motivos.append("Hubo un compromiso y no hay evidencia posterior que lo confirme.")
    if e.contrato.verbos_permitidos and not e.compromisos and not e.sin_cambios_justificados:
        motivos.append("La tarea pedía un cambio y no se ejecutó ningún compromiso.")
    if e.contrato.pregunta and not e.respuesta and not e.sin_respuesta_posible:
        motivos.append("La pregunta quedó sin respuesta.")

    if motivos:
        return ResultadoEstado(estado="fallida", motivos=tuple(motivos))
    return ResultadoEstado(estado="terminada")
