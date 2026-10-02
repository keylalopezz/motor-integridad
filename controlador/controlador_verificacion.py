from typing import List, Dict, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.validador import Validador
from modelo.verificador import VerificadorBatch

class ControladorVerificacion:
    def __init__(self, usuario: str):
        self.validador = Validador(usuario)
        self.verificador = VerificadorBatch(usuario)

    def validar_insercion(self, motor: str, coleccion: str, registro: Dict) -> tuple[bool, str]:
        return self.validador.validar_registro(motor, coleccion, registro)

    def ejecutar_verificacion_batch(self) -> Tuple[List[Dict], List[str]]:
        violaciones = self.verificador.ejecutar_verificacion()
        return violaciones, self.verificador.errores
