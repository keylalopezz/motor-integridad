"""Conexión única (singleton) con Supabase y lectura de configuración."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from .registro_logs import obtener_logger

load_dotenv()
log = obtener_logger("supabase")


def obtener_config(nombre: str, defecto: str = "") -> str:
    """Lee una variable de entorno (.env local) o de st.secrets (Streamlit Cloud)."""
    valor = os.environ.get(nombre)
    if valor:
        return valor
    try:
        import streamlit as st
        if nombre in st.secrets:
            return str(st.secrets[nombre])
    except Exception:
        pass
    return defecto


class SupabaseClient:
    """Singleton que crea el cliente de Supabase con ``SUPABASE_URL`` y ``SUPABASE_KEY``."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            url: str = obtener_config("SUPABASE_URL")
            key: str = obtener_config("SUPABASE_KEY")
            if url and key:
                try:
                    cls._instance.client: Client = create_client(url, key)
                except Exception as e:
                    cls._instance.client = None
                    log.error("Error al inicializar Supabase: %s", e)
            else:
                cls._instance.client = None
                log.warning("No se encontraron credenciales de Supabase (.env o st.secrets)")
        return cls._instance

    def get_client(self) -> Client:
        """Devuelve el cliente de Supabase o ``None`` si faltan credenciales."""
        return self.client
