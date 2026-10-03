from typing import Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.autenticacion import Autenticacion

class ControladorAuth:
    def __init__(self):
        self.auth = Autenticacion()

    def registrar(self, usuario: str, password: str) -> Tuple[bool, str]:
        return self.auth.registrar_usuario(usuario, password)

    def login(self, usuario: str, password: str) -> Tuple[bool, str, Optional[str]]:
        return self.auth.verificar_login(usuario, password)

    def actualizar_actividad(self, usuario: str):
        self.auth.actualizar_actividad(usuario)

    def obtener_usuarios_activos(self, minutos: int = 5) -> list:
        return self.auth.obtener_usuarios_activos(minutos=minutos)
