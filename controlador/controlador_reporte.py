"""Controlador de reportes de anomalías."""

from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.log_auditoria import LogAuditoria

class ControladorReporte:
    """Consulta las violaciones registradas de un usuario."""
    def __init__(self, usuario: str):
        self.auditoria = LogAuditoria(usuario)

    def obtener_violaciones(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """Devuelve las violaciones, opcionalmente filtradas."""
        return self.auditoria.obtener_violaciones(filtros)
