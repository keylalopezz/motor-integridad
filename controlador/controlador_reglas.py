"""Controlador de reglas de integridad."""

from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.motor_reglas import MotorReglas
from modelo.metricas_uso import MetricasUso

class ControladorReglas:
    """Operaciones sobre las reglas de un usuario."""
    def __init__(self, usuario: str):
        self.motor = MotorReglas(usuario)
        self.metricas = MetricasUso(usuario)

    def crear_regla(self, regla: Dict) -> Dict:
        """Crea una regla y registra el evento de uso."""
        creada = self.motor.crear_regla(regla)
        self.metricas.registrar("regla", {"tipo": regla.get("tipo"), "motor": regla.get("motor_origen")})
        return creada

    def obtener_reglas(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """Devuelve las reglas del usuario."""
        return self.motor.obtener_reglas(filtros)

    def eliminar_regla(self, regla_id: str) -> bool:
        """Elimina una regla por su id."""
        return self.motor.eliminar_regla(regla_id)
