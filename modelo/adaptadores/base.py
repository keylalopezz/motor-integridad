"""Interfaz común que implementan los adaptadores de MongoDB, Redis y Cassandra."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class Adaptador(ABC):
    """Contrato abstracto de acceso a un motor NoSQL usado por el validador y el escaneo batch."""
    @abstractmethod
    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        """Verifica si existe un registro con el campo y valor dados."""
        pass

    @abstractmethod
    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        """Obtiene registros de la coleccion dado un filtro."""
        pass

    @abstractmethod
    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        """Cuenta cuantos registros tienen el mismo valor en un campo especificado."""
        pass

    @abstractmethod
    def obtener_todos(self, coleccion: str) -> List[Dict]:
        """Obtiene todos los registros de una coleccion."""
        pass

    @abstractmethod
    def verificar_salud(self) -> Dict[str, Any]:
        """Verifica conectividad y latencia con el motor."""
        pass

    @abstractmethod
    def listar_recursos(self) -> List[Dict[str, Any]]:
        """Lista colecciones, tablas o prefijos de claves."""
        pass

    @abstractmethod
    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        """Obtiene una muestra representativa de registros de una coleccion/tabla."""
        pass

    def obtener_info_completa(self) -> Dict[str, Any]:
        """Obtiene telemetria avanzada, esquema e inventario completo del motor NoSQL."""
        return {}

    def cerrar(self) -> None:
        """Cierra la conexion o pool de conexiones si aplica."""
        pass
