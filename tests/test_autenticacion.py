import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo import autenticacion as mod


def crear_auth(usuarios_existentes=()):
    supabase = MagicMock()
    tabla = supabase.table.return_value
    tabla.select.return_value.ilike.return_value.execute.return_value.data = [{"id": 1}] if usuarios_existentes else []
    with patch.object(mod, "SupabaseClient") as sc:
        sc.return_value.get_client.return_value = supabase
        return mod.Autenticacion(), tabla


def test_rechaza_usuario_con_espacios_internos():
    auth, tabla = crear_auth()
    ok, msj = auth.registrar_usuario("ana maria", "secreto1")
    assert not ok and "sin espacios" in msj
    tabla.insert.assert_not_called()


def test_rechaza_usuario_corto_y_password_corta():
    auth, _ = crear_auth()
    assert not auth.registrar_usuario("ab", "secreto1")[0]
    assert not auth.registrar_usuario("ana", "123")[0]


def test_quita_espacios_al_registrar():
    auth, tabla = crear_auth()
    ok, _ = auth.registrar_usuario("  Gordo  ", "secreto1")
    assert ok
    assert tabla.insert.call_args[0][0]["usuario"] == "Gordo"


def test_duplicado_sin_distinguir_mayusculas():
    auth, tabla = crear_auth(usuarios_existentes=["gordo"])
    ok, msj = auth.registrar_usuario("GORDO", "secreto1")
    assert not ok and "ya existe" in msj
    tabla.select.return_value.ilike.assert_called_with("usuario", "GORDO")
    tabla.insert.assert_not_called()


def test_guion_bajo_se_escapa_en_la_busqueda():
    auth, tabla = crear_auth()
    auth.registrar_usuario("user_1", "secreto1")
    tabla.select.return_value.ilike.assert_called_with("usuario", r"user\_1")


def crear_auth_login(filas):
    supabase = MagicMock()
    tabla = supabase.table.return_value
    tabla.select.return_value.ilike.return_value.execute.return_value.data = filas
    with patch.object(mod, "SupabaseClient") as sc:
        sc.return_value.get_client.return_value = supabase
        return mod.Autenticacion(), tabla


def _hash(password):
    return mod.bcrypt.hashpw(password.encode(), mod.bcrypt.gensalt(4)).decode()


def test_login_sin_distinguir_mayusculas_devuelve_nombre_registrado():
    auth, tabla = crear_auth_login([{"usuario": "Keyla", "password_hash": _hash("secreto1")}])
    assert auth.verificar_login("keyla", "secreto1") == (True, "Login exitoso.", "Keyla")
    tabla.select.return_value.ilike.assert_called_with("usuario", "keyla")


def test_login_rechaza_password_incorrecta():
    auth, _ = crear_auth_login([{"usuario": "Keyla", "password_hash": _hash("secreto1")}])
    ok, _, usuario = auth.verificar_login("Keyla", "otra")
    assert not ok and usuario is None


def test_login_no_acepta_comodines():
    auth, tabla = crear_auth_login([{"usuario": "Keyla", "password_hash": _hash("secreto1")}])
    assert not auth.verificar_login("%", "secreto1")[0]
    tabla.select.assert_not_called()
