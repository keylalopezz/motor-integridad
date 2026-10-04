"""Registro y consulta de los eventos de utilización del producto (tabla ``eventos_uso``)."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from .supabase_client import SupabaseClient

ACCIONES = {
    "login": "Inicio de sesión",
    "registro": "Cuenta creada",
    "conexion": "Conexión guardada",
    "regla": "Regla creada",
    "validacion": "Validación pre-escritura",
    "escaneo": "Scan Batch",
}


class MetricasUso:
    """Guarda y lee los eventos de uso del Motor de Integridad.

    Si la tabla ``eventos_uso`` todavía no existe (migración pendiente), la aplicación sigue
    funcionando: ``registrar`` no hace nada y ``obtener_eventos`` devuelve ``None``.
    """

    def __init__(self, usuario: Optional[str] = None):
        """Crea el registro para ``usuario``; sin usuario solo permite consultas globales."""
        self.usuario = usuario
        self.supabase = SupabaseClient().get_client()

    def registrar(self, accion: str, detalle: Optional[Dict] = None) -> None:
        """Guarda un evento ``accion`` (clave de ``ACCIONES``) con datos adicionales opcionales."""
        if not self.supabase or not self.usuario:
            return
        try:
            self.supabase.table('eventos_uso').insert(
                {'usuario': self.usuario, 'accion': accion, 'detalle': detalle or {}}).execute()
        except Exception as e:
            print(f"No se pudo registrar el evento de uso: {type(e).__name__}")

    def obtener_eventos(self, dias: int = 30, todos: bool = False) -> Optional[List[Dict]]:
        """Devuelve los eventos de los últimos ``dias``; con ``todos`` incluye a todos los usuarios.

        Devuelve ``None`` si la tabla no está disponible.
        """
        if not self.supabase:
            return None
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        try:
            consulta = self.supabase.table('eventos_uso').select('usuario, accion, creado_en').gte('creado_en', desde)
            if not todos:
                consulta = consulta.eq('usuario', self.usuario)
            return consulta.order('creado_en').limit(10000).execute().data or []
        except Exception:
            return None
