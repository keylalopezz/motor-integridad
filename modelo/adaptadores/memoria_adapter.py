"""Adaptador en memoria: colecciones de diccionarios que se comportan como un motor NoSQL.

Lo usa ``motor demo`` para ejecutar el motor de reglas sobre el conjunto de prueba sin conectarse a
ninguna base de datos, y demuestra la extensibilidad de la arquitectura (RNF11): basta implementar
la interfaz ``Adaptador`` para que el validador y el escaneo funcionen con una nueva fuente de datos.
"""

import copy
import json
from typing import Any, Dict, List

from .base import Adaptador


class MemoriaAdapter(Adaptador):
    """Motor NoSQL simulado: ``{coleccion: [registros]}``."""

    def __init__(self, colecciones: Dict[str, List[Dict[str, Any]]], nombre: str = "memoria"):
        self.colecciones = colecciones
        self.nombre = nombre

    def _registros(self, coleccion: str) -> List[Dict[str, Any]]:
        return self.colecciones.get(coleccion, [])

    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        return any(r.get(campo) == valor for r in self._registros(coleccion))

    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        return [copy.deepcopy(r) for r in self._registros(coleccion)
                if all(r.get(k) == v for k, v in filtro.items())]

    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        return sum(1 for r in self._registros(coleccion) if r.get(campo) == valor)

    def obtener_todos(self, coleccion: str) -> List[Dict]:
        return copy.deepcopy(self._registros(coleccion))

    def verificar_salud(self) -> Dict[str, Any]:
        return {"estado": "Disponible", "latencia_ms": 0.0, "detalle": f"{self.nombre} (memoria)"}

    def listar_recursos(self) -> List[Dict[str, Any]]:
        return [{"nombre": c, "registros": len(r)} for c, r in self.colecciones.items()]

    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        return self.obtener_todos(coleccion)[:limite]


def cargar_motores(ruta: str) -> Dict[str, MemoriaAdapter]:
    """Lee un JSON ``{motor: {coleccion: [registros]}}`` y crea un adaptador por motor."""
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return {motor: MemoriaAdapter(colecciones, motor) for motor, colecciones in datos.items()}
