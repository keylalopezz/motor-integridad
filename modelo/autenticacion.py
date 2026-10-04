"""Registro, inicio de sesión y actividad de los usuarios (tabla ``usuarios_sistema``)."""

import re
from datetime import datetime, timezone, timedelta
import bcrypt
from typing import Dict, Tuple, Optional
from .supabase_client import SupabaseClient

USUARIO_VALIDO = re.compile(r"[A-Za-z0-9_-]{3,30}")

class Autenticacion:
    """Gestiona las cuentas de la plataforma con contraseñas cifradas con bcrypt."""
    def __init__(self):
        """Obtiene el cliente de Supabase."""
        self.supabase = SupabaseClient().get_client()

    def registrar_usuario(self, usuario: str, password: str) -> Tuple[bool, str]:
        """Crea una cuenta tras validar el nombre (3-30 caracteres) y la contraseña (mínimo 6).

        Devuelve ``(exito, mensaje)``; rechaza duplicados sin distinguir mayúsculas.
        """
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

    def verificar_login(self, usuario: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """Devuelve (exito, mensaje, usuario tal como esta registrado). El nombre no distingue mayusculas."""
        if not self.supabase:
            return False, "Error de conexión a Supabase.", None

        usuario = (usuario or "").strip()
        # Validar antes de usar ilike: el patron no admite comodines como "%"
        if not USUARIO_VALIDO.fullmatch(usuario):
            return False, "Usuario o contraseña incorrectos.", None
        try:
            res = self.supabase.table('usuarios_sistema').select('usuario, password_hash').ilike('usuario', usuario.replace('_', r'\_')).execute()
        except Exception as e:
            print(f"Error al verificar login: {e}")
            return False, "No se pudo conectar con el servidor de autenticación. Intenta de nuevo en unos minutos.", None

        # Cuentas antiguas pueden diferir solo en mayusculas: se prueba primero la coincidencia exacta
        candidatos = sorted(res.data or [], key=lambda r: r['usuario'] != usuario)
        for fila in candidatos:
            if bcrypt.checkpw(password.encode('utf-8'), fila['password_hash'].encode('utf-8')):
                self.actualizar_actividad(fila['usuario'])
                return True, "Login exitoso.", fila['usuario']
        return False, "Usuario o contraseña incorrectos.", None

    def actualizar_actividad(self, usuario: str):
        """Registra la fecha de la última actividad del usuario."""
        if self.supabase:
            try:
                ahora = datetime.now(timezone.utc).isoformat()
                self.supabase.table('usuarios_sistema').update({'ultimo_acceso': ahora}).eq('usuario', usuario).execute()
            except Exception:
                pass

    def obtener_usuarios_activos(self, minutos: int = 5) -> list:
        """Devuelve los usuarios con actividad en los últimos ``minutos``."""
        if not self.supabase:
            return []
        try:
            # En supabase postgrest, filtramos los que tengan ultimo_acceso >= now() - X minutes.
            # Una forma simple es traer todos (si son pocos) o usar un query.
            # Para evitar logica compleja de datetime en string, traemos y filtramos en python por simplicidad
            res = self.supabase.table('usuarios_sistema').select('usuario, ultimo_acceso').execute()
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
