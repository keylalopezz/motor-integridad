import json
from typing import Any, Dict, List, Optional
from .supabase_client import SupabaseClient


def a_json(valor: Any) -> Any:
    """Convierte tipos no serializables (ObjectId, UUID, datetime, Decimal...) para guardarlos en jsonb."""
    return json.loads(json.dumps(valor, default=str))


class LogAuditoria:
    def __init__(self, usuario: str):
        self.usuario = usuario
        self.supabase = SupabaseClient().get_client()

    def registrar_violacion(self, violacion: Dict) -> Dict:
        res = self.registrar_violaciones([violacion])
        return res[0] if res else {}

    def registrar_violaciones(self, violaciones: List[Dict]) -> List[Dict]:
        if not self.supabase or not violaciones:
            return []
        filas = [{**a_json(v), 'usuario': self.usuario} for v in violaciones]
        insertadas = []
        # Lotes para no exceder el tamaño de peticion de PostgREST
        for i in range(0, len(filas), 500):
            response = self.supabase.table('auditoria_violaciones').insert(filas[i:i + 500]).execute()
            insertadas.extend(response.data or [])
        return insertadas

    def limpiar_regla(self, regla_id: str) -> None:
        """Elimina las violaciones previas de una regla para que un nuevo escaneo no las duplique."""
        if self.supabase:
            self.supabase.table('auditoria_violaciones').delete().eq('usuario', self.usuario).eq('regla_id', regla_id).execute()

    def obtener_violaciones(self, filtros: Optional[Dict] = None) -> List[Dict]:
        if not self.supabase:
            return []
        query = self.supabase.table('auditoria_violaciones').select('*, reglas(tipo, motor_origen, coleccion_origen)').eq('usuario', self.usuario)
        if filtros:
            for k, v in filtros.items():
                query = query.eq(k, v)
        query = query.order('detectado_en', desc=True)
        response = query.execute()
        return response.data
