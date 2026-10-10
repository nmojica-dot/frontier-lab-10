"""Borrado de secretos. Falla en cerrado: si algo queda, lanza en vez de dejarlo pasar."""

import json
import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import quote, quote_plus

MARCA = "[secreto]"

# Formas de llave conocidas, por si el secreto no se le pasó a la función.
_PATRONES = [
    re.compile(r"sk-or-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"),
]


class SecretoSinRedactar(Exception):
    """Tras redactar sigue apareciendo un secreto. El texto no debe guardarse ni emitirse."""


def _variantes(secreto: str) -> set[str]:
    return {
        secreto,
        quote(secreto, safe=""),
        quote_plus(secreto),
        json.dumps(secreto)[1:-1],
    }


def _prepara(secretos: Iterable[str]) -> list[str]:
    todas: set[str] = set()
    for s in secretos:
        if not s:
            raise ValueError("Un secreto vacío borraría todo el texto: revisa de dónde sale.")
        todas |= _variantes(s)
    return sorted(todas, key=len, reverse=True)


def redactar(texto: str, secretos: Iterable[str]) -> str:
    lista = _prepara(secretos)
    for v in lista:
        texto = texto.replace(v, MARCA)
    for patron in _PATRONES:
        texto = patron.sub(MARCA, texto)
    if any(v in texto for v in lista):
        raise SecretoSinRedactar("Quedó un secreto en el texto tras redactar.")
    return texto


def redactar_datos(dato: Any, secretos: Iterable[str]) -> Any:
    """Redacta cadenas dentro de dict/list/tuple (cargas de eventos). Claves incluidas."""
    lista = list(secretos)
    if isinstance(dato, str):
        return redactar(dato, lista)
    if isinstance(dato, dict):
        return {redactar_datos(k, lista): redactar_datos(v, lista) for k, v in dato.items()}
    if isinstance(dato, (list, tuple)):
        return [redactar_datos(v, lista) for v in dato]
    return dato
