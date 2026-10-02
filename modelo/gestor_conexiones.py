import json
from typing import Dict, Optional
from .supabase_client import SupabaseClient, obtener_config

# Las credenciales de los motores se guardan cifradas con Fernet si existe
# ENCRYPTION_KEY. Las configuraciones antiguas (en texto plano) se siguen leyendo.
_CAMPO_CIFRADO = "_cifrado"


def _fernet():
    clave = obtener_config("ENCRYPTION_KEY")
    if not clave:
        return None
    from cryptography.fernet import Fernet
    return Fernet(clave.encode("utf-8"))


class GestorConexiones:
    def __init__(self, usuario: str):
        self.usuario = usuario
        self.supabase = SupabaseClient().get_client()

    def _cifrar(self, config: Dict) -> Dict:
        f = _fernet()
        if not f:
            return config
        token = f.encrypt(json.dumps(config).encode("utf-8")).decode("utf-8")
        return {_CAMPO_CIFRADO: token}

    def _descifrar(self, config: Optional[Dict]) -> Optional[Dict]:
        if not config or _CAMPO_CIFRADO not in config:
            return config
        f = _fernet()
        if not f:
            raise RuntimeError("La conexion esta cifrada pero falta ENCRYPTION_KEY en la configuracion.")
        return json.loads(f.decrypt(config[_CAMPO_CIFRADO].encode("utf-8")))

    def guardar_conexion(self, motor: str, config: Dict) -> Dict:
        if not self.supabase:
            return {}
        data = {
            "usuario": self.usuario,
            "motor": motor,
            "config": self._cifrar(config)
        }
        # Supabase upsert requires specifying the conflicting columns for composite keys
        response = self.supabase.table('conexiones_motores').upsert(data, on_conflict='usuario,motor').execute()
        return response.data[0] if response.data else {}

    def obtener_conexion(self, motor: str) -> Optional[Dict]:
        if not self.supabase:
            return None
        response = self.supabase.table('conexiones_motores').select('*').eq('usuario', self.usuario).eq('motor', motor).execute()
        if response.data:
            return self._descifrar(response.data[0].get('config'))
        return None

    def motores_configurados(self) -> list:
        if not self.supabase:
            return []
        response = self.supabase.table('conexiones_motores').select('motor').eq('usuario', self.usuario).execute()
        return [r['motor'] for r in response.data]

    def eliminar_conexion(self, motor: str) -> None:
        if self.supabase:
            self.supabase.table('conexiones_motores').delete().eq('usuario', self.usuario).eq('motor', motor).execute()
