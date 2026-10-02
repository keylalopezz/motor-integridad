from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.log_auditoria import LogAuditoria

class ControladorReporte:
    def __init__(self, usuario: str):
        self.auditoria = LogAuditoria(usuario)

    def obtener_violaciones(self, filtros: Optional[Dict] = None) -> List[Dict]:
        return self.auditoria.obtener_violaciones(filtros)
