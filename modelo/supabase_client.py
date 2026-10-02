import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


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
                    print(f"Error al inicializar Supabase: {e}")
            else:
                cls._instance.client = None
                print("Advertencia: No se encontraron credenciales de Supabase (.env o st.secrets)")
        return cls._instance

    def get_client(self) -> Client:
        return self.client
