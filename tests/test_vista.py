"""Pruebas de humo de las páginas Streamlit (``streamlit.testing``) con los datos de Supabase simulados."""

import os
import sys
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(RAIZ)
from vista import cache

RUTAS = os.path.join(RAIZ, "vista", "rutas")
VIOLACIONES = [
    {"regla_id": "r1", "tipo": "unicidad", "motores_involucrados": "mongodb", "dato_afectado": {"_id": "U004"},
     "detectado_en": "2026-11-14T10:00:00+00:00", "reglas": {"tipo": "unicidad", "coleccion_origen": "usuarios"}},
    {"regla_id": "r2", "tipo": "referencial", "motores_involucrados": "cassandra,mongodb", "dato_afectado": {"id": "PA3"},
     "detectado_en": "2026-11-14T10:00:00+00:00"},
]
EVENTOS = [
    {"usuario": "Keyla", "accion": "escaneo", "creado_en": "2026-11-14T10:00:00+00:00",
     "detalle": {"anomalias": 2, "duracion_ms": 1500, "origen": "web"}},
    {"usuario": "Keyla", "accion": "escaneo", "creado_en": "2026-11-14T11:00:00+00:00",
     "detalle": {"anomalias": 2, "duracion_ms": 900, "origen": "cli"}},
    {"usuario": "Keyla", "accion": "reporte_excel", "creado_en": "2026-11-14T11:05:00+00:00", "detalle": {}},
]
REGLAS = [{"id": "r1", "tipo": "unicidad", "motor_origen": "mongodb", "coleccion_origen": "usuarios", "campo": "email",
           "creado_en": "2026-11-14T09:00:00"}]


@pytest.fixture
def datos(monkeypatch):
    """Sustituye las lecturas cacheadas por datos fijos (sin Supabase)."""
    monkeypatch.setattr(cache, "violaciones", lambda usuario: VIOLACIONES)
    monkeypatch.setattr(cache, "reglas", lambda usuario: REGLAS)
    monkeypatch.setattr(cache, "motores", lambda usuario: ["mongodb", "cassandra"])
    monkeypatch.setattr(cache, "github_configurado", lambda usuario: "org/repo")
    monkeypatch.setattr(cache, "eventos", lambda usuario, dias, todos: EVENTOS)
    monkeypatch.setattr(cache, "historial", lambda usuario, accion, limite=20: [e for e in EVENTOS if e["accion"] == accion])
    monkeypatch.setattr(cache, "invalidar", lambda: None)


def pagina(nombre: str) -> AppTest:
    app = AppTest.from_file(os.path.join(RUTAS, nombre), default_timeout=60)
    app.session_state["logged_in"] = True
    app.session_state["usuario"] = "Keyla"
    return app.run()


def sin_errores(app: AppTest) -> AppTest:
    assert not app.exception, [e.value for e in app.exception]
    return app


def test_reportes_ofrece_pdf_excel_y_github(datos):
    app = sin_errores(pagina("6_Reportes.py"))
    assert "Se detectaron 2 anomalía(s)" in app.warning[0].value
    assert any("Crear Issue en org/repo" in b.label for b in app.button)
    assert len(app.expander) == 2


def test_reportes_crea_el_issue(datos):
    app = pagina("6_Reportes.py")
    with patch("modelo.integraciones.github_issues.publicar_anomalias") as publicar:
        publicar.return_value = {"numero": 5, "url": "https://github.com/org/repo/issues/5"}
        boton = next(b for b in app.button if "Crear Issue" in b.label)
        app = sin_errores(boton.click().run())
    publicar.assert_called_once()
    assert "Issue #5 creado" in app.success[0].value


def test_dashboard_muestra_utilizacion_y_telemetria(datos):
    app = sin_errores(pagina("3_Dashboard.py"))
    metricas = {m.label: m.value for m in app.metric}
    assert metricas["Anomalías Detectadas"] == "2"
    assert metricas["Acciones desde la CLI"] == "1"
    assert metricas["Duración media del escaneo"] == "1.2 s"
    assert metricas["Reportes exportados"] == "1"


def test_ejecucion_muestra_el_historial_de_escaneos(datos):
    app = sin_errores(pagina("2_Verificacion.py"))
    assert app.checkbox[0].label.startswith("Publicar el resultado como Issue")
    assert len(app.dataframe) == 1


def test_conexiones_incluye_la_integracion_con_github(datos):
    app = pagina("0_Conexiones.py")
    app.selectbox[0].select("GitHub (integración)")
    app = sin_errores(app.run())
    assert any("Repositorio" in t.label for t in app.text_input)


def test_reglas_y_monitor_cargan(datos):
    sin_errores(pagina("1_Reglas.py"))
    app = sin_errores(pagina("5_Monitor.py"))
    assert any("Logs de tu actividad" in s.value for s in app.subheader)


def test_app_sin_supabase_muestra_error_controlado():
    app = AppTest.from_file(os.path.join(RAIZ, "vista", "app.py"), default_timeout=60).run()
    assert not app.exception
    assert "No se pudo conectar con Supabase" in app.error[0].value


@pytest.fixture
def supabase_simulado():
    from unittest.mock import MagicMock
    from modelo.supabase_client import SupabaseClient
    cliente = MagicMock()
    with patch.object(SupabaseClient, "get_client", return_value=cliente):
        yield cliente


def app_con_sesion(**estado) -> AppTest:
    app = AppTest.from_file(os.path.join(RAIZ, "vista", "app.py"), default_timeout=60)
    app.session_state["logged_in"] = True
    app.session_state["usuario"] = "Keyla"
    for clave, valor in estado.items():
        app.session_state[clave] = valor
    return app.run()


def test_sesion_activa_muestra_su_duracion(datos, supabase_simulado):
    import time
    app = sin_errores(app_con_sesion(inicio_sesion=time.time() - 600))
    assert any("Sesión activa hace 10 min" in c.value for c in app.sidebar.caption)


def test_sesion_expira_por_inactividad(datos, supabase_simulado):
    import time
    app = sin_errores(app_con_sesion(inicio_sesion=time.time() - 7200, ultima_interaccion=time.time() - 3600))
    assert app.session_state["logged_in"] is False
    assert "expiró" in app.warning[0].value
    insertados = [c.args[0] for c in supabase_simulado.table.return_value.insert.call_args_list]
    assert any(fila.get("accion") == "sesion_expirada" for fila in insertados)
