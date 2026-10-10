import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_token: str
    db_path: str = "navegante.db"
    cuadros_dir: str = "capturas"
    worker_demora: float = 2.0
    sse_latido: float = 15.0
    openrouter_api_key: str = ""
    costo_max_por_tarea: float = 0.50

    @classmethod
    def desde_entorno(cls) -> "Settings":
        return cls(
            api_token=os.environ.get("API_TOKEN", ""),
            db_path=os.environ.get("DB_PATH", "navegante.db"),
            cuadros_dir=os.environ.get("CUADROS_DIR", "capturas"),
            worker_demora=float(os.environ.get("WORKER_DEMORA", "2")),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            costo_max_por_tarea=float(os.environ.get("COSTO_MAX_POR_TAREA", "0.50")),
        )
