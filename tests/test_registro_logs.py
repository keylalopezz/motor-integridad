"""Pruebas del módulo de logs y del adaptador en memoria."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.adaptadores.base import Adaptador
from modelo.adaptadores.memoria_adapter import MemoriaAdapter
from modelo.registro_logs import obtener_logger, registros_recientes


def test_los_logs_quedan_en_memoria_por_usuario():
    log = obtener_logger("pruebas")
    log.info("Escaneo de prueba", extra={"usuario": "ana-test"})
    log.warning("Aviso de otro usuario", extra={"usuario": "luis-test"})

    propios = registros_recientes("ana-test")
    assert propios[0]["mensaje"] == "Escaneo de prueba"
    assert propios[0]["nivel"] == "INFO" and propios[0]["modulo"] == "motor.pruebas"
    assert all(r["usuario"] == "ana-test" for r in propios)
    assert any(r["mensaje"] == "Aviso de otro usuario" for r in registros_recientes())


def test_adaptador_en_memoria_cumple_la_interfaz():
    adp = MemoriaAdapter({"c": [{"_id": 1, "x": "a"}, {"_id": 2, "x": "a"}]})
    assert isinstance(adp, Adaptador)
    assert adp.existe("c", "_id", 2) and not adp.existe("c", "_id", 3)
    assert adp.contar_duplicados("c", "x", "a") == 2
    assert adp.obtener("c", {"_id": 1}) == [{"_id": 1, "x": "a"}]
    todos = adp.obtener_todos("c")
    todos[0]["x"] = "cambiado"
    assert adp.obtener_todos("c")[0]["x"] == "a"  # devuelve copias
    assert adp.verificar_salud()["estado"] == "Disponible"
    assert adp.listar_recursos() == [{"nombre": "c", "registros": 2}]
