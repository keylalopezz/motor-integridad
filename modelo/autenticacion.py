import re
import bcrypt
from typing import Dict, Tuple, Optional
from .supabase_client import SupabaseClient

USUARIO_VALIDO = re.compile(r"[A-Za-z0-9_-]{3,30}")

class Autenticacion:
    def __init__(self):
        self.supabase = SupabaseClient().get_client()

    def registrar_usuario(self, usuario: str, password: str) -> Tuple[bool, str]:
        if not self.supabase:
            return False, "Error de conexión a Supabase."

        usuario = (usuario or "").strip()
        if not USUARIO_VALIDO.fullmatch(usuario):
            return False, "El usuario debe tener de 3 a 30 caracteres: letras, números, guion o guion bajo, sin espacios."
        if len(password or "") < 6:
            return False, "La contraseña debe tener al menos 6 caracteres."

        try:
            # ilike sin comodines compara sin distinguir mayusculas: evita "Ana" y "ana" como cuentas distintas
            # "_" es comodin en LIKE: se escapa para comparar el nombre literal
            res = self.supabase.table('usuarios_sistema').select('id').ilike('usuario', usuario.replace('_', r'\_')).execute()
            if res.data:
                return False, "El usuario ya existe."

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            self.supabase.table('usuarios_sistema').insert({
                "usuario": usuario,
                "password_hash": password_hash
            }).execute()
            return True, "Usuario registrado exitosamente."
        except Exception as e:
            print(f"Error al registrar usuario: {e}")
            return False, "No se pudo registrar el usuario. Intenta de nuevo en unos minutos."

    def verificar_login(self, usuario: str, password: str) -> Tuple[bool, str]:
        if not self.supabase:
            return False, "Error de conexión a Supabase."

        usuario = (usuario or "").strip()
        try:
            res = self.supabase.table('usuarios_sistema').select('password_hash').eq('usuario', usuario).execute()
        except Exception as e:
            print(f"Error al verificar login: {e}")
            return False, "No se pudo conectar con el servidor de autenticación. Intenta de nuevo en unos minutos."
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
