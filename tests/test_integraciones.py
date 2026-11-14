"""Pruebas de las integraciones: reporte Excel (Office) e Issues de GitHub (API simulada)."""

import io
import json
import os
import sys
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from openpyxl import load_workbook

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.descripcion_anomalias import describir, id_registro, resumen_por_tipo
from modelo.integraciones import github_issues as gh
from modelo.integraciones.excel import COLUMNAS, generar_excel

VIOLACIONES = [
    {"regla_id": "R1", "tipo": "esquema", "motores_involucrados": "mongodb", "dato_afectado": {"_id": "U003"}},
    {"regla_id": "R2", "tipo": "unicidad", "motores_involucrados": "mongodb", "dato_afectado": {"_id": "U004"}},
    {"regla_id": "R6", "tipo": "referencial", "motores_involucrados": "cassandra,mongodb", "dato_afectado": {"id": "PA3"}},
    {"regla_id": "R4", "tipo": "consistencia", "motores_involucrados": "mongodb,redis",
     "dato_afectado": {"_id": "U001", "diferencias": {"edad": {"origen": 28, "destino": 29}}}},
]
REGLAS = {"R1": {"coleccion_origen": "usuarios", "campo": "_id"}, "R6": {"coleccion_origen": "pagos", "campo": "pedido_id"}}


# ---------------------------------------------------------------- descripciones

def test_describir_usa_id_o__id_y_los_motores():
    d = describir(VIOLACIONES[2])
    assert d["id"] == "PA3" and d["titulo"] == "Integridad referencial"
    assert "huérfano" in d["explicacion"]
    assert "mongodb,redis" in describir(VIOLACIONES[3])["explicacion"]


def test_describir_tipo_desconocido_no_falla():
    d = describir({"tipo": "otro", "dato_afectado": None})
    assert d["id"] == "Desconocido" and d["sugerencia"]
    assert id_registro("texto") == "Desconocido"


def test_resumen_por_tipo_incluye_los_cuatro_tipos():
    assert resumen_por_tipo(VIOLACIONES) == {"esquema": 1, "unicidad": 1, "referencial": 1, "consistencia": 1}
    assert resumen_por_tipo([]) == {"esquema": 0, "unicidad": 0, "referencial": 0, "consistencia": 0}


# ---------------------------------------------------------------- Excel

def test_excel_tiene_resumen_y_detalle_con_tabla_filtrable():
    libro = load_workbook(io.BytesIO(generar_excel(VIOLACIONES, usuario="Keyla", origen="pruebas", reglas=REGLAS)))
    assert libro.sheetnames == ["Resumen", "Anomalías"]
    resumen = {fila[0]: fila[1] for fila in libro["Resumen"].iter_rows(values_only=True) if fila[0]}
    assert resumen["Usuario"] == "Keyla" and resumen["Total de anomalías"] == 4
    assert resumen["Esquema"] == 1 and resumen["Consistencia"] == 1

    detalle = libro["Anomalías"]
    assert [c.value for c in detalle[1]] == COLUMNAS
    assert detalle.max_row == 5 and "Anomalias" in detalle.tables
    fila = [c.value for c in detalle[2]]
    assert fila[1] == "Esquema" and fila[3] == "usuarios" and fila[5] == "U003"
    assert json.loads(fila[9]) == {"_id": "U003"}


def test_excel_toma_la_coleccion_del_join_de_supabase():
    v = {**VIOLACIONES[1], "reglas": {"coleccion_origen": "clientes"}, "detectado_en": "2026-11-14T10:00:00"}
    detalle = load_workbook(io.BytesIO(generar_excel([v])))["Anomalías"]
    assert detalle["D2"].value == "clientes" and detalle["I2"].value == "2026-11-14T10:00:00"


def test_excel_sin_anomalias_es_valido():
    libro = load_workbook(io.BytesIO(generar_excel([])))
    assert libro["Anomalías"].max_row == 1 and not libro["Anomalías"].tables


# ---------------------------------------------------------------- GitHub

def respuesta(datos):
    resp = MagicMock()
    resp.read.return_value = json.dumps(datos).encode("utf-8")
    resp.__enter__.return_value = resp
    return resp


def error_http(codigo):
    return urllib.error.HTTPError("https://api.github.com", codigo, "error", {}, io.BytesIO(b"{}"))


def test_construir_issue_resume_y_detalla():
    titulo, cuerpo = gh.construir_issue(VIOLACIONES, ["Regla x: timeout"], usuario="Keyla", reglas=REGLAS)
    assert titulo.startswith("⚠️ 4 anomalía(s)")
    assert "| 📐 Esquema | 1 |" in cuerpo and "`PA3`" in cuerpo and "| pagos |" in cuerpo
    assert "Reglas no evaluadas" in cuerpo and "Regla x: timeout" in cuerpo


def test_construir_issue_sin_anomalias_y_tabla_limitada():
    assert gh.construir_issue([])[0].startswith("✅ Escaneo sin anomalías")
    _, cuerpo = gh.construir_issue(VIOLACIONES * 20)
    assert f"Se muestran {gh.MAX_FILAS} de 80" in cuerpo


def test_crear_issue_envia_token_titulo_y_etiqueta():
    with patch.object(gh.urllib.request, "urlopen", return_value=respuesta({"number": 7, "html_url": "https://x/7"})) as urlopen:
        issue = gh.IntegracionGitHub("tok", "https://github.com/duenio-1/repo.x/").crear_issue("T", "C")
    assert issue == {"numero": 7, "url": "https://x/7"}
    req = urlopen.call_args[0][0]
    assert req.full_url == "https://api.github.com/repos/duenio-1/repo.x/issues"
    assert req.get_method() == "POST" and req.headers["Authorization"] == "Bearer tok"
    assert json.loads(req.data) == {"title": "T", "body": "C", "labels": gh.ETIQUETAS}


def test_crear_issue_reintenta_sin_etiquetas_si_github_las_rechaza():
    with patch.object(gh.urllib.request, "urlopen", side_effect=[error_http(422), respuesta({"number": 8})]) as urlopen:
        assert gh.IntegracionGitHub("tok", "a/b").crear_issue("T", "C")["numero"] == 8
    assert "labels" not in json.loads(urlopen.call_args[0][0].data)


@pytest.mark.parametrize("codigo, texto", [(401, "no es válido"), (404, "No se encontró"), (410, "desactivados")])
def test_errores_http_se_traducen(codigo, texto):
    with patch.object(gh.urllib.request, "urlopen", side_effect=error_http(codigo)):
        with pytest.raises(gh.ErrorGitHub, match=texto):
            gh.IntegracionGitHub("tok", "a/b").verificar()


def test_repositorio_y_token_obligatorios():
    with pytest.raises(gh.ErrorGitHub, match="formato"):
        gh.IntegracionGitHub("tok", "sin-barra")
    with pytest.raises(gh.ErrorGitHub, match="token"):
        gh.IntegracionGitHub("", "a/b")


def test_configuracion_de_github_actions_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t-actions")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    assert gh.configuracion_github("Keyla") == {"GITHUB_TOKEN": "t-actions", "GITHUB_REPO": "org/repo"}


def test_configuracion_guardada_por_el_usuario(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with patch("modelo.gestor_conexiones.GestorConexiones") as gc:
        gc.return_value.obtener_conexion.return_value = {"GITHUB_TOKEN": "t", "GITHUB_REPO": "a/b"}
        assert gh.configuracion_github("Keyla")["GITHUB_REPO"] == "a/b"
        gc.return_value.obtener_conexion.assert_called_with("github")
    assert gh.configuracion_github(None) is None


def test_publicar_sin_configuracion_explica_que_hacer(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(gh.ErrorGitHub, match="no está configurado"):
        gh.publicar_anomalias(VIOLACIONES)
