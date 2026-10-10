"""Nombres de tecla y caracteres a keysyms de X11, que es lo que habla RFB."""

_MODIFICADORES = {
    "ctrl": 0xFFE3,
    "control": 0xFFE3,
    "shift": 0xFFE1,
    "mayus": 0xFFE1,
    "alt": 0xFFE9,
}

_ESPECIALES = {
    "enter": 0xFF0D,
    "return": 0xFF0D,
    "tab": 0xFF09,
    "escape": 0xFF1B,
    "esc": 0xFF1B,
    "backspace": 0xFF08,
    "delete": 0xFFFF,
    "supr": 0xFFFF,
    "home": 0xFF50,
    "left": 0xFF51,
    "up": 0xFF52,
    "right": 0xFF53,
    "down": 0xFF54,
    "pageup": 0xFF55,
    "pagedown": 0xFF56,
    "end": 0xFF57,
    "space": 0x20,
    **_MODIFICADORES,
    **{f"f{n}": 0xFFBD + n for n in range(1, 13)},
}


def keysym_de_caracter(c: str) -> int:
    """Keysym de un carácter. Latin-1 usa su código; el resto, el rango Unicode de X11."""
    if c == "\n":
        return _ESPECIALES["enter"]
    if c == "\t":
        return _ESPECIALES["tab"]
    if len(c) != 1 or ord(c) < 0x20 or 0x7F <= ord(c) < 0xA0:
        raise ValueError(f"carácter no tecleable: {c!r}")
    return ord(c) if ord(c) <= 0xFF else 0x01000000 + ord(c)


def keysyms_de_combinacion(nombre: str) -> list[int]:
    """`"enter"`, `"ctrl+a"`, `"ctrl+shift+Left"` -> keysyms en orden de pulsación."""
    if len(nombre) == 1:
        return [keysym_de_caracter(nombre)]
    partes = nombre.split("+")
    if "" in partes:
        raise ValueError(f"combinación inválida: {nombre!r}")
    simbolos = []
    for i, parte in enumerate(partes):
        clave = parte.lower()
        if clave in _ESPECIALES:
            simbolos.append(_ESPECIALES[clave])
        elif len(parte) == 1 and i == len(partes) - 1:
            # Con modificadores la letra va en minúscula: ctrl+A no debe implicar shift.
            simbolos.append(keysym_de_caracter(clave if len(partes) > 1 else parte))
        else:
            raise ValueError(f"tecla desconocida: {parte!r}")
    return simbolos
