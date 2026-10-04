"""Adaptadores de los motores NoSQL y fábrica ``get_adapter``."""

from .mongo_adapter import MongoAdapter
from .redis_adapter import RedisAdapter
from .cassandra_adapter import CassandraAdapter
from ..gestor_conexiones import GestorConexiones

MOTORES_SOPORTADOS = ['mongodb', 'redis', 'cassandra']


def get_adapter(motor: str, usuario: str):
    """Crea el adaptador del ``motor`` (mongodb, redis o cassandra) con las credenciales guardadas de ``usuario``.

    Lanza ``ValueError`` si el motor no está soportado o no tiene conexión configurada.
    """
    motor = motor.lower()
    if motor not in MOTORES_SOPORTADOS:
        raise ValueError(f"Motor no soportado: {motor}")

    config = GestorConexiones(usuario).obtener_conexion(motor)
    if not config:
        raise ValueError(f"No hay credenciales guardadas para {motor.upper()}. Configuralo en 'Bases de Datos'.")

    if motor == 'mongodb':
        return MongoAdapter(config)
    elif motor == 'redis':
        return RedisAdapter(config)
    return CassandraAdapter(config)
