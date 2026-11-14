"""Registro de logs del Motor de Integridad (módulo estándar ``logging``).

Cada evento se escribe en tres destinos:

- la consola (salida de error), visible en los logs de Streamlit Cloud y de GitHub Actions;
- el archivo rotativo ``logs/motor.log`` (1 MB x 3 archivos);
- un búfer en memoria con los últimos registros, que la página Monitor muestra a cada usuario
  (solo sus propios eventos, identificados con ``extra={"usuario": ...}``).

Configuración por variables de entorno: ``LOG_LEVEL`` (INFO por defecto) y ``LOG_DIR``.
"""

import logging
import os
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional

RAIZ = "motor"
FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_CAPACIDAD_MEMORIA = 1000


class BuferMemoria(logging.Handler):
    """Guarda los últimos registros en memoria para consultarlos desde la aplicación."""

    def __init__(self, capacidad: int = _CAPACIDAD_MEMORIA):
        super().__init__()
        self.registros: deque = deque(maxlen=capacidad)

    def emit(self, record: logging.LogRecord) -> None:
        """Almacena el registro ya formateado junto con su usuario."""
        try:
            self.registros.append({
                "fecha": self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S") if self.formatter else "",
                "nivel": record.levelname,
                "modulo": record.name,
                "usuario": getattr(record, "usuario", None),
                "mensaje": record.getMessage(),
            })
        except Exception:
            self.handleError(record)


_bufer: Optional[BuferMemoria] = None
_consola: Optional[logging.Handler] = None


def configurar_logs() -> logging.Logger:
    """Configura (una sola vez) el logger raíz ``motor`` con consola, archivo y búfer en memoria."""
    global _bufer, _consola
    logger = logging.getLogger(RAIZ)
    if _bufer is not None:
        return logger

    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    formato = logging.Formatter(FORMATO)

    _consola = logging.StreamHandler()
    _consola.setFormatter(formato)
    logger.addHandler(_consola)

    carpeta = os.environ.get("LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    try:
        os.makedirs(carpeta, exist_ok=True)
        archivo = RotatingFileHandler(os.path.join(carpeta, "motor.log"), maxBytes=1_000_000,
                                      backupCount=3, encoding="utf-8")
        archivo.setFormatter(formato)
        logger.addHandler(archivo)
    except OSError:
        # Sistema de archivos de solo lectura: se mantienen la consola y la memoria
        pass

    _bufer = BuferMemoria()
    _bufer.setFormatter(formato)
    logger.addHandler(_bufer)
    return logger


def obtener_logger(nombre: str) -> logging.Logger:
    """Devuelve el logger ``motor.<nombre>`` (configura el registro la primera vez)."""
    configurar_logs()
    return logging.getLogger(f"{RAIZ}.{nombre}")


def nivel_consola(nivel: int) -> None:
    """Cambia el nivel mínimo que se muestra en la consola (la CLI solo muestra advertencias)."""
    configurar_logs()
    if _consola is not None:
        _consola.setLevel(nivel)


def registros_recientes(usuario: Optional[str] = None, limite: int = 200) -> List[Dict]:
    """Últimos registros en memoria, más recientes primero; con ``usuario`` solo los suyos."""
    configurar_logs()
    filas = [r for r in reversed(_bufer.registros) if usuario is None or r["usuario"] == usuario]
    return filas[:limite]
