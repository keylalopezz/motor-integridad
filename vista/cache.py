"""Caché de lecturas de la vista (``st.cache_data``) para no consultar Supabase en cada interacción.

Streamlit vuelve a ejecutar la página completa con cada clic; sin caché, cada clic repetía las
consultas de reglas, anomalías, conexiones y métricas. Las funciones guardan el resultado por
``usuario`` durante ``TTL`` segundos (el usuario forma parte de la clave, por lo que nunca se
comparten datos entre cuentas). Toda operación que modifica datos llama a ``invalidar()``.
"""

import os
import sys
from typing import Dict, List, Optional

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from controlador.controlador_reglas import ControladorReglas
from controlador.controlador_reporte import ControladorReporte
from modelo.gestor_conexiones import GestorConexiones
from modelo.metricas_uso import MetricasUso

TTL = 60


@st.cache_data(ttl=TTL, show_spinner=False)
def reglas(usuario: str) -> List[Dict]:
    """Reglas activas del usuario."""
    return ControladorReglas(usuario).obtener_reglas()


@st.cache_data(ttl=TTL, show_spinner=False)
def violaciones(usuario: str) -> List[Dict]:
    """Anomalías registradas del usuario (más recientes primero)."""
    return ControladorReporte(usuario).obtener_violaciones()


@st.cache_data(ttl=TTL, show_spinner=False)
def motores(usuario: str) -> List[str]:
    """Motores NoSQL con conexión guardada."""
    return GestorConexiones(usuario).motores_configurados()


@st.cache_data(ttl=TTL, show_spinner=False)
def github_configurado(usuario: str) -> Optional[str]:
    """Repositorio de GitHub configurado por el usuario, o ``None``."""
    config = GestorConexiones(usuario).obtener_conexion("github") or {}
    return config.get("GITHUB_REPO")


@st.cache_data(ttl=TTL, show_spinner=False)
def eventos(usuario: str, dias: int, todos: bool) -> Optional[List[Dict]]:
    """Eventos de uso del periodo (``None`` si la tabla no existe)."""
    return MetricasUso(usuario).obtener_eventos(dias=dias, todos=todos)


@st.cache_data(ttl=TTL, show_spinner=False)
def historial(usuario: str, accion: str, limite: int = 20) -> List[Dict]:
    """Últimos eventos ``accion`` del usuario con su detalle."""
    return MetricasUso(usuario).obtener_historial(accion, limite)


def invalidar() -> None:
    """Descarta la caché después de crear, eliminar o escanear (los datos cambiaron)."""
    for funcion in (reglas, violaciones, motores, github_configurado, eventos, historial):
        funcion.clear()
