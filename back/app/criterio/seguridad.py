"""Reglas de seguridad: qué acción se puede ejecutar y desempate de registros."""

import re

from app.criterio.contrato import (
    Accion,
    ContratoCambios,
    Decision,
    EstadoCriterio,
    Origen,
)


def _ok() -> Decision:
    return Decision(resultado="permitida")


def _no(motivo: str, *, fallida: bool = True) -> Decision:
    return Decision(resultado="denegada", motivo=motivo, fallida=fallida)


def validar_accion(
    contrato: ContratoCambios, accion: Accion, estado: EstadoCriterio, origen: Origen
) -> Decision:
    """Decide si `accion` se ejecuta. La app nunca entra aquí: solo el contrato."""
    if accion.tipo in ("leer", "navegar"):
        return _ok()
    if accion.tipo == "escribir":
        return _validar_escritura(contrato, accion)
    return _validar_compromiso(contrato, accion, estado, origen)


def _validar_escritura(contrato: ContratoCambios, accion: Accion) -> Decision:
    if accion.campo is None or accion.valor is None:
        return _no("Escritura sin campo o sin valor: no se puede comprobar contra el contrato.")
    permitidos = contrato.valores_permitidos.get(accion.campo)
    if permitidos is None:
        return _no(f"El campo '{accion.campo}' no sale de la instrucción; no se escribe.")
    if accion.valor not in permitidos:
        # No se imprime el valor: puede ser un secreto tecleado por error.
        return _no(f"El valor para '{accion.campo}' no sale de la instrucción; no se escribe.")
    return _ok()


def _validar_compromiso(
    contrato: ContratoCambios, accion: Accion, estado: EstadoCriterio, origen: Origen
) -> Decision:
    verbo = accion.verbo
    if verbo is None:
        return _no("Compromiso sin verbo: no se sabe qué se estaría haciendo.")
    if verbo not in contrato.verbos_permitidos:
        return _no(f"La instrucción no permite '{verbo}'.")
    if verbo in estado.compromisos:
        return _no(f"'{verbo}' ya se intentó una vez; no se repite a ciegas.")
    if estado.registros_coincidentes is None:
        # Al crear aún se puede buscar y reintentar; en lo demás, sin verificar la tarea cierra.
        return _no(f"No se verificó el registro antes de '{verbo}'.", fallida=not contrato.crea)
    if contrato.crea and verbo == "guardar":
        if estado.registros_coincidentes > 0:
            return _no(
                f"Ya existe {estado.registros_coincidentes} registro con esos datos: "
                "no se crea un duplicado."
            )
        return _ok()
    if estado.registros_coincidentes != 1:
        return _no(
            f"Para '{verbo}' se necesita exactamente un registro verificado y hay "
            f"{estado.registros_coincidentes}."
        )
    if verbo == "eliminar":
        return _validar_eliminar(accion, estado, origen)
    return _ok()


def _validar_eliminar(accion: Accion, estado: EstadoCriterio, origen: Origen) -> Decision:
    if accion.registros_afectados is None:
        return _no("No se sabe cuántos registros borraría la acción; no se toca nada.")
    if accion.registros_afectados != 1:
        return _no(
            f"Borrado masivo bloqueado: la acción afectaría {accion.registros_afectados} "
            "registros. No se tocó nada."
        )
    if origen == "chat" and not estado.eliminacion_confirmada:
        return Decision(
            resultado="confirmacion",
            motivo="Falta que la persona confirme la eliminación del registro completo.",
        )
    return _ok()


def _norm(texto: str) -> str:
    return " ".join(texto.split()).casefold()


def desempatar(
    contrato: ContratoCambios, candidatos: list[dict[str, str]], origen: Origen
) -> tuple[Decision, list[dict[str, str]]]:
    """Filtra candidatos solo con datos de la instrucción. Nunca elige el 'más probable'.

    Devuelve la decisión y los candidatos que quedaron. Con uno: permitida.
    Con ninguno: fallida. Con varios: pregunta (chat) o fallida nombrando los
    identificadores (api).
    """
    objetivo = {k: _norm(v) for k, v in contrato.registro_objetivo.items()}
    restantes = [
        c for c in candidatos if all(_norm(c.get(k, "")) == v for k, v in objetivo.items())
    ]
    if len(restantes) == 1:
        return _ok(), restantes
    if not restantes:
        return _no("No existe ningún registro que coincida con la instrucción."), []
    ids = "; ".join(", ".join(f"{k}={v}" for k, v in sorted(c.items())) for c in restantes)
    if origen == "chat":
        return (
            Decision(
                resultado="pregunta",
                motivo=f"Hay {len(restantes)} registros posibles y la instrucción no desempata: {ids}",
            ),
            restantes,
        )
    return (
        _no(f"Hay {len(restantes)} registros posibles y la instrucción no desempata: {ids}"),
        restantes,
    )


# Frases típicas de una nota que da órdenes. Es solo para mencionarlas en el
# resumen; la protección real es que el contrato no cambia con texto de la app.
_ORDENES = re.compile(
    r"\b(ignora|ignore|olvida|borra|elimina|delete|remove|cambia|modifica|env[ií]a|"
    r"exporta|guarda|haz|debes|por favor|instrucci[oó]n|ahora)\b",
    re.IGNORECASE,
)


def detectar_ordenes(texto_app: str) -> bool:
    """True si el texto leído de la app parece pedir algo. Nunca se obedece."""
    return _ORDENES.search(texto_app) is not None
