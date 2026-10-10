"""Armado del resumen. Lo escribe el código, no el modelo, y sale sin secretos."""

from collections.abc import Iterable
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.criterio.redaccion import redactar

Valor = int | float | Decimal | str


class EntradaResumen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    estado: str  # "terminada" | "fallida"
    hecho: tuple[str, ...] = ()
    no_confirmado: tuple[str, ...] = ()
    motivos: tuple[str, ...] = ()
    notas_app_ignoradas: tuple[str, ...] = ()
    respuesta: tuple[Valor, ...] = ()


def formatear_valor(valor: Valor) -> str:
    """Número sin separador de miles ni notación científica; texto tal cual."""
    if isinstance(valor, bool):
        raise TypeError("Un booleano no es un dato de respuesta.")
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, (float, Decimal)):
        dec = Decimal(str(valor))
        if not dec.is_finite():
            raise ValueError("Número no finito en la respuesta.")
        texto = format(dec, "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return texto
    if not valor.strip() or any(c in valor for c in "\n\r;"):
        raise ValueError("Un dato de respuesta no puede estar vacío ni tener salto de línea o ';'.")
    return valor.strip()


def linea_respuesta(valores: tuple[Valor, ...]) -> str | None:
    """`respuesta: <valor>`; números primero; dos datos con `;`. Sin datos: None."""
    if not valores:
        return None
    if len(valores) > 2:
        raise ValueError("La respuesta admite como máximo dos datos.")
    ordenados = sorted(valores, key=lambda v: isinstance(v, str))  # estable: números antes
    return "respuesta: " + "; ".join(formatear_valor(v) for v in ordenados)


def armar_resumen(entrada: EntradaResumen, secretos: Iterable[str]) -> str:
    if entrada.estado not in ("terminada", "fallida"):
        raise ValueError(f"Estado no válido para un resumen: {entrada.estado!r}")
    lineas: list[str] = []
    if entrada.estado == "terminada":
        lineas.append("Tarea terminada.")
    else:
        lineas.append("La tarea no se pudo completar.")
    lineas += [f"- {m}" for m in entrada.motivos]
    if entrada.hecho:
        lineas.append("Lo que se hizo:")
        lineas += [f"- {h}" for h in entrada.hecho]
    if entrada.no_confirmado:
        lineas.append("Lo que no se pudo confirmar:")
        lineas += [f"- {n}" for n in entrada.no_confirmado]
    if entrada.notas_app_ignoradas:
        lineas.append("La app mostró texto que pedía algo; no se obedeció:")
        lineas += [f"- {n}" for n in entrada.notas_app_ignoradas]
    respuesta = linea_respuesta(entrada.respuesta)
    if respuesta:
        lineas.append(respuesta)
    return redactar("\n".join(lineas), secretos)
