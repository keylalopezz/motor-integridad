import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo import metricas_uso as mod


def crear_metricas(usuario="Keyla", falla=False):
    supabase = MagicMock()
    if falla:
        supabase.table.side_effect = RuntimeError("relation eventos_uso does not exist")
    with patch.object(mod, "SupabaseClient") as sc:
        sc.return_value.get_client.return_value = supabase
        return mod.MetricasUso(usuario), supabase


def test_registra_evento_con_usuario():
    metricas, supabase = crear_metricas()
    metricas.registrar("escaneo", {"anomalias": 7})
    fila = supabase.table.return_value.insert.call_args[0][0]
    assert fila == {"usuario": "Keyla", "accion": "escaneo", "detalle": {"anomalias": 7}}


def test_sin_tabla_no_interrumpe_la_app():
    metricas, _ = crear_metricas(falla=True)
    metricas.registrar("login")
    assert metricas.obtener_eventos() is None


def test_sin_usuario_no_registra():
    metricas, supabase = crear_metricas(usuario=None)
    metricas.registrar("login")
    supabase.table.assert_not_called()
