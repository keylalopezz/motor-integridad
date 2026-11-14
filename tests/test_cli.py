"""Pruebas de la CLI ``motor`` (sin cuenta ni bases de datos: demo y validación con esquema)."""

import json
import os
import sys
from unittest.mock import patch

import pytest
from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(RAIZ)
from motor_cli import main as cli

EJEMPLOS = os.path.join(RAIZ, "ejemplos")
ESQUEMA = os.path.join(EJEMPLOS, "esquema_usuario.json")


def correr(capsys, *args):
    codigo = cli.main(list(args))
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def test_demo_detecta_las_siete_violaciones_del_conjunto_de_prueba(capsys):
    codigo, out, _ = correr(capsys, "demo", "--json")
    datos = json.loads(out)
    assert codigo == cli.OK and datos["errores"] == []
    assert len(datos["anomalias"]) == 7
    assert datos["resumen"] == {"esquema": 2, "unicidad": 2, "referencial": 2, "consistencia": 1}
    detectados = {(a["regla_id"], a["dato_afectado"].get("_id") or a["dato_afectado"].get("id")) for a in datos["anomalias"]}
    assert detectados == {("R1", "U003"), ("R2", "U004"), ("R3", "P102"), ("R4", "U001"),
                          ("R5", "U003"), ("R6", "PA3"), ("R7", "PA4")}


def test_demo_en_texto_y_modo_estricto(capsys):
    codigo, out, _ = correr(capsys, "demo", "--estricto")
    assert codigo == cli.INVALIDO
    assert "Anomalías detectadas: 7" in out and "PA4" in out


def test_demo_genera_el_excel(capsys, tmp_path):
    destino = tmp_path / "sub" / "reporte.xlsx"
    codigo, out, _ = correr(capsys, "demo", "--excel", str(destino))
    assert codigo == cli.OK and destino.exists() and "Reporte Excel guardado" in out
    assert load_workbook(destino)["Anomalías"].max_row == 8


def test_demo_publica_el_issue_con_la_configuracion_de_github(capsys):
    with patch("modelo.integraciones.github_issues.configuracion_github", return_value={"GITHUB_TOKEN": "t", "GITHUB_REPO": "a/b"}), \
            patch("modelo.integraciones.github_issues.IntegracionGitHub") as ig:
        ig.return_value.crear_issue.return_value = {"numero": 3, "url": "https://github.com/a/b/issues/3"}
        codigo, out, _ = correr(capsys, "demo", "--github-issue")
    assert codigo == cli.OK and "Issue #3 creado" in out
    ig.assert_called_once_with("t", "a/b")
    titulo, cuerpo = ig.return_value.crear_issue.call_args[0]
    assert "7 anomalía(s)" in titulo and "PA3" in cuerpo


def test_demo_sin_github_configurado_termina_con_error_claro(capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    codigo, _, err = correr(capsys, "demo", "--github-issue")
    assert codigo == cli.ERROR_CONEXION and "no está configurado" in err


def test_demo_con_datos_propios(capsys, tmp_path):
    datos = tmp_path / "datos.json"
    reglas = tmp_path / "reglas.json"
    datos.write_text(json.dumps({"mongodb": {"c": [{"_id": 1, "x": "a"}, {"_id": 2, "x": "a"}]}}), encoding="utf-8")
    reglas.write_text(json.dumps([{"id": "U", "tipo": "unicidad", "motor_origen": "mongodb",
                                   "coleccion_origen": "c", "campo": "x"}]), encoding="utf-8")
    codigo, out, _ = correr(capsys, "demo", "--datos", str(datos), "--reglas", str(reglas), "--json")
    assert codigo == cli.OK and len(json.loads(out)["anomalias"]) == 1


@pytest.mark.parametrize("archivo, codigo_esperado, invalidos", [
    ("registro_valido.json", 0, 0), ("registro_invalido.json", 1, 1), ("registros_lote.json", 1, 2)])
def test_validar_con_esquema(capsys, archivo, codigo_esperado, invalidos):
    codigo, out, _ = correr(capsys, "validar", os.path.join(EJEMPLOS, archivo), "--esquema", ESQUEMA)
    assert codigo == codigo_esperado
    assert f"{invalidos} inválido(s)" in out


def test_validar_indica_el_campo_que_falla(capsys):
    codigo, out, _ = correr(capsys, "validar", os.path.join(EJEMPLOS, "registro_invalido.json"), "-e", ESQUEMA, "--json")
    resultado = json.loads(out)[0]
    assert codigo == cli.INVALIDO and resultado["registro"] == "U011" and not resultado["valido"]
    assert "'email' is a required property" in resultado["mensaje"] and "edad:" in resultado["mensaje"]


def test_validar_errores_de_uso(capsys, tmp_path):
    malo = tmp_path / "malo.json"
    malo.write_text("{no es json", encoding="utf-8")
    assert correr(capsys, "validar", str(malo), "-e", ESQUEMA)[0] == cli.ERROR_USO
    assert correr(capsys, "validar", "no-existe.json", "-e", ESQUEMA)[0] == cli.ERROR_USO
    codigo, _, err = correr(capsys, "validar", os.path.join(EJEMPLOS, "registro_valido.json"))
    assert codigo == cli.ERROR_USO and "--esquema" in err


def test_esquema_invalido(capsys, tmp_path):
    esquema = tmp_path / "esquema.json"
    esquema.write_text(json.dumps({"type": "no-existe"}), encoding="utf-8")
    codigo, _, err = correr(capsys, "validar", os.path.join(EJEMPLOS, "registro_valido.json"), "-e", str(esquema))
    assert codigo == cli.ERROR_USO and "no es un JSON Schema válido" in err


def test_comandos_con_cuenta_piden_configuracion(capsys, monkeypatch):
    monkeypatch.setattr("modelo.supabase_client.obtener_config", lambda nombre, defecto="": "")
    codigo, _, err = correr(capsys, "escanear", "--usuario", "ana")
    assert codigo == cli.ERROR_USO and "SUPABASE_URL" in err


def test_escanear_con_cuenta_usa_el_controlador(capsys, monkeypatch):
    monkeypatch.setattr("modelo.supabase_client.obtener_config", lambda nombre, defecto="": "x")
    monkeypatch.setenv("MOTOR_PASSWORD", "secreto")
    violacion = {"regla_id": "r1", "tipo": "unicidad", "motores_involucrados": "mongodb", "dato_afectado": {"_id": "U9"}}
    with patch("controlador.controlador_auth.ControladorAuth") as auth, \
            patch("controlador.controlador_reglas.ControladorReglas") as reglas, \
            patch("controlador.controlador_verificacion.ControladorVerificacion") as verif:
        auth.return_value.login.return_value = (True, "ok", "Ana")
        reglas.return_value.obtener_reglas.return_value = [{"id": "r1", "coleccion_origen": "usuarios"}]
        verif.return_value.ejecutar_verificacion_batch.return_value = ([violacion], [])
        codigo, out, _ = correr(capsys, "escanear", "--usuario", "ana")
    assert codigo == cli.OK and "U9" in out and "usuarios" in out
    auth.return_value.login.assert_called_once_with("ana", "secreto")
    verif.assert_called_once_with("Ana", origen="cli")


def test_login_incorrecto(capsys, monkeypatch):
    monkeypatch.setattr("modelo.supabase_client.obtener_config", lambda nombre, defecto="": "x")
    monkeypatch.setenv("MOTOR_PASSWORD", "mala")
    with patch("controlador.controlador_auth.ControladorAuth") as auth:
        auth.return_value.login.return_value = (False, "Usuario o contraseña incorrectos.", None)
        codigo, _, err = correr(capsys, "reglas", "--usuario", "ana")
    assert codigo == cli.ERROR_USO and "incorrectos" in err


def test_ayuda_y_version(capsys):
    assert correr(capsys, )[0] == cli.ERROR_USO
    with pytest.raises(SystemExit) as salida:
        cli.main(["--version"])
    assert salida.value.code == 0 and "motor 2.0.0" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["demo", "--help"])
    assert "conjunto de prueba" in capsys.readouterr().out
