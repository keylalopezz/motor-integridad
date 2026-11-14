"""Controlador de autenticación."""

from typing import Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.autenticacion import Autenticacion
from modelo.metricas_uso import MetricasUso
from modelo.registro_logs import obtener_logger

log = obtener_logger("sesiones")

class ControladorAuth:
    """Registro, inicio de sesión y actividad de usuarios para la vista."""
    def __init__(self):
        self.auth = Autenticacion()

    def registrar(self, usuario: str, password: str) -> Tuple[bool, str]:
        """Crea una cuenta; devuelve ``(exito, mensaje)``."""
        exito, mensaje = self.auth.registrar_usuario(usuario, password)
        if exito:
            MetricasUso((usuario or "").strip()).registrar("registro")
        return exito, mensaje

    def login(self, usuario: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """Verifica credenciales; devuelve ``(exito, mensaje, usuario_registrado)``."""
        exito, mensaje, registrado = self.auth.verificar_login(usuario, password)
        if exito:
            MetricasUso(registrado).registrar("login")
        return exito, mensaje, registrado

    def cerrar_sesion(self, usuario: str, motivo: str = "logout", duracion_min: float = 0) -> None:
        """Registra el cierre (``logout``) o la expiración (``sesion_expirada``) de la sesión."""
        MetricasUso(usuario).registrar(motivo, {"duracion_min": duracion_min})
        log.info("Sesión finalizada (%s) tras %.1f min", motivo, duracion_min, extra={"usuario": usuario})

    def actualizar_actividad(self, usuario: str):
        """Marca la actividad reciente del usuario."""
        self.auth.actualizar_actividad(usuario)

    def obtener_usuarios_activos(self, minutos: int = 5) -> list:
        """Lista los usuarios activos en los últimos ``minutos``."""
        return self.auth.obtener_usuarios_activos(minutos=minutos)
