from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.motor_reglas import MotorReglas

class ControladorReglas:
    def __init__(self, usuario: str):
        self.motor = MotorReglas(usuario)

    def crear_regla(self, regla: Dict) -> Dict:
        return self.motor.crear_regla(regla)

    def obtener_reglas(self, filtros: Optional[Dict] = None) -> List[Dict]:
        return self.motor.obtener_reglas(filtros)

    def eliminar_regla(self, regla_id: str) -> bool:
        return self.motor.eliminar_regla(regla_id)
