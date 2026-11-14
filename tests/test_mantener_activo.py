"""Pruebas del script que mantiene activos los servicios gratuitos (servicios simulados)."""

import os
import sys
from unittest.mock import MagicMock, patch

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(RAIZ, "scripts"))
import mantener_activo as ma


def test_reintenta_hasta_que_el_servicio_responde():
    llamadas = []

    def servicio():
        llamadas.append(1)
        if len(llamadas) < 2:
            raise ConnectionError("hibernado")
        return "ok"

    ok, detalle, _ = ma.con_reintentos(servicio, intentos=3, espera=0)
    assert ok and detalle == "ok" and len(llamadas) == 2
    ok, detalle, _ = ma.con_reintentos(lambda: 1 / 0, intentos=2, espera=0)
    assert not ok and "ZeroDivisionError" in detalle


def supabase_falso(conexiones):
    cliente = MagicMock()
    usuarios, conex = MagicMock(), MagicMock()
    usuarios.select.return_value.limit.return_value.execute.return_value.data = [{"id": 1}]
    conex.select.return_value.eq.return_value.execute.return_value.data = conexiones
    cliente.table.side_effect = lambda nombre: usuarios if nombre == "usuarios_sistema" else conex
    return cliente


def test_revisa_supabase_y_cada_motor_del_usuario():
    conexiones = [{"usuario": "Keyla", "motor": "mongodb"}, {"usuario": "Keyla", "motor": "cassandra"},
                  {"usuario": "Keyla", "motor": "github"}]
    adaptador = MagicMock()
    adaptador.verificar_salud.return_value = {"estado": "Disponible", "detalle": "tienda"}
    with patch("modelo.supabase_client.SupabaseClient") as sc, \
            patch("modelo.adaptadores.get_adapter", return_value=adaptador) as fabrica:
        sc.return_value.get_client.return_value = supabase_falso(conexiones)
        filas = ma.revisar_bases("Keyla")
    assert [f[0] for f in filas] == ["Supabase", "Mongodb (Keyla)", "Cassandra (Keyla)"]
    assert all(f[1] == "✅ activo" for f in filas)
    assert fabrica.call_count == 2 and adaptador.cerrar.call_count == 2


def test_sin_secretos_y_sin_app_no_falla(monkeypatch, tmp_path):
    for variable in ("SUPABASE_URL", "SUPABASE_KEY", "ENCRYPTION_KEY", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(ma, "SALIDA", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["mantener_activo.py", "--sin-app"])
    assert ma.main() == 0
    assert "Faltan los secretos" in (tmp_path / "reporte.md").read_text(encoding="utf-8")


def test_un_servicio_caido_hace_fallar_el_flujo(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "x")
    monkeypatch.setenv("SUPABASE_KEY", "x")
    monkeypatch.setenv("ENCRYPTION_KEY", "x")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ma, "SALIDA", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["mantener_activo.py", "--sin-app"])
    monkeypatch.setattr(ma, "revisar_bases", lambda usuario: [("Supabase", "❌ error", "pausado", 0.0)])
    assert ma.main() == 1
