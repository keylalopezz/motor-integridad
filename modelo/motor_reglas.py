"""Gestión de las reglas de integridad (tabla ``reglas``)."""

from typing import List, Dict, Optional
from .supabase_client import SupabaseClient

class MotorReglas:
    """Crea, consulta, actualiza y elimina las reglas de un usuario."""
    def __init__(self, usuario: str):
        """Crea el gestor de reglas para ``usuario``."""
        self.usuario = usuario
        self.supabase = SupabaseClient().get_client()

    def crear_regla(self, regla: Dict) -> Dict:
        """Guarda una regla (esquema, unicidad, referencial o consistencia) y la devuelve."""
        if not self.supabase:
            return {}
        regla['usuario'] = self.usuario
        response = self.supabase.table('reglas').insert(regla).execute()
        return response.data[0] if response.data else {}

    def obtener_reglas(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """Devuelve las reglas del usuario, opcionalmente filtradas por columnas."""
        if not self.supabase:
            return []
        query = self.supabase.table('reglas').select('*').eq('usuario', self.usuario)
        if filtros:
            for k, v in filtros.items():
                query = query.eq(k, v)
        response = query.execute()
        return response.data

    def actualizar_regla(self, regla_id: str, datos: Dict) -> Dict:
        """Actualiza los campos ``datos`` de la regla ``regla_id``."""
        if not self.supabase:
            return {}
        response = self.supabase.table('reglas').update(datos).eq('usuario', self.usuario).eq('id', regla_id).execute()
        return response.data[0] if response.data else {}

    def eliminar_regla(self, regla_id: str) -> bool:
        """Elimina la regla ``regla_id``; devuelve ``True`` si se eliminó."""
        if not self.supabase:
            return False
        response = self.supabase.table('reglas').delete().eq('usuario', self.usuario).eq('id', regla_id).execute()
        return len(response.data) > 0
