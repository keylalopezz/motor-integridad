import bcrypt
from typing import Dict, Tuple, Optional
from .supabase_client import SupabaseClient

class Autenticacion:
    def __init__(self):
        self.supabase = SupabaseClient().get_client()

    def registrar_usuario(self, usuario: str, password: str) -> Tuple[bool, str]:
        if not self.supabase:
            return False, "Error de conexion a Supabase."
        
        # Check if user exists
        res = self.supabase.table('usuarios_sistema').select('id').eq('usuario', usuario).execute()
        if res.data:
            return False, "El usuario ya existe."
            
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            self.supabase.table('usuarios_sistema').insert({
                "usuario": usuario,
                "password_hash": password_hash
            }).execute()
            return True, "Usuario registrado exitosamente."
        except Exception as e:
            return False, f"Error al registrar: {e}"

    def verificar_login(self, usuario: str, password: str) -> Tuple[bool, str]:
        if not self.supabase:
            return False, "Error de conexion a Supabase."
            
        res = self.supabase.table('usuarios_sistema').select('password_hash').eq('usuario', usuario).execute()
        if not res.data:
            return False, "Usuario o contraseña incorrectos."
            
        stored_hash = res.data[0]['password_hash']
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            self.actualizar_actividad(usuario)
            return True, "Login exitoso."
        else:
            return False, "Usuario o contraseña incorrectos."

    def actualizar_actividad(self, usuario: str):
        if self.supabase:
            try:
                self.supabase.table('usuarios_sistema').update({'ultimo_acceso': 'now()'}).eq('usuario', usuario).execute()
            except:
                pass

    def obtener_usuarios_activos(self, minutos: int = 5) -> list:
        if not self.supabase:
            return []
        try:
            # En supabase postgrest, filtramos los que tengan ultimo_acceso >= now() - X minutes.
            # Una forma simple es traer todos (si son pocos) o usar un query.
            # Para evitar logica compleja de datetime en string, traemos y filtramos en python por simplicidad
            res = self.supabase.table('usuarios_sistema').select('usuario, ultimo_acceso').execute()
            from datetime import datetime, timezone, timedelta
            activos = []
            ahora = datetime.now(timezone.utc)
            for r in res.data:
                if r.get('ultimo_acceso'):
                    try:
                        # Supabase returns ISO format: 2026-09-24T20:41:25.123+00:00
                        ua = datetime.fromisoformat(r['ultimo_acceso'].replace('Z', '+00:00'))
                        if ahora - ua <= timedelta(minutes=minutos):
                            activos.append(r['usuario'])
                    except:
                        pass
            return activos
        except:
            return []
