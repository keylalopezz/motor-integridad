"""Controlador de validación y escaneo por lotes."""

from typing import List, Dict, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.validador import Validador
from modelo.verificador import VerificadorBatch
from modelo.metricas_uso import MetricasUso

class ControladorVerificacion:
    """Ejecuta la validación pre-escritura y el Scan Batch."""
    def __init__(self, usuario: str):
        self.validador = Validador(usuario)
        self.verificador = VerificadorBatch(usuario)
        self.metricas = MetricasUso(usuario)

    def validar_insercion(self, motor: str, coleccion: str, registro: Dict) -> tuple[bool, str]:
        """Valida un registro antes de escribirlo; devuelve ``(valido, mensaje)``."""
        valido, mensaje = self.validador.validar_registro(motor, coleccion, registro)
        self.metricas.registrar("validacion", {"motor": motor, "coleccion": coleccion, "valido": valido})
        return valido, mensaje

    def ejecutar_verificacion_batch(self) -> Tuple[List[Dict], List[str]]:
        """Escanea todos los motores; devuelve ``(violaciones, errores)``."""
        violaciones = self.verificador.ejecutar_verificacion()
        self.metricas.registrar("escaneo", {"anomalias": len(violaciones), "errores": len(self.verificador.errores)})
        return violaciones, self.verificador.errores
