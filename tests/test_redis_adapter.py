import sys
import os
from unittest.mock import MagicMock

import redis

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.adaptadores.redis_adapter import RedisAdapter, SIN_PREFIJO


def crear_adaptador(claves):
    """claves: {nombre: (tipo, valor)} simulando un servidor Redis."""
    adp = RedisAdapter.__new__(RedisAdapter)
    cli = MagicMock()

    def scan_iter(match=None, count=None):
        prefijo = match[:-1] if match else ""
        return iter([k for k in claves if k.startswith(prefijo)])

    def get(k):
        tipo, valor = claves[k]
        if tipo != "string":
            raise redis.exceptions.ResponseError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return valor

    cli.scan_iter.side_effect = scan_iter
    cli.get.side_effect = get
    cli.type.side_effect = lambda k: claves[k][0]
    cli.hgetall.side_effect = lambda k: claves[k][1]
    adp.client = cli
    return adp


def test_lee_json_y_hash_e_ignora_otras_estructuras():
    adp = crear_adaptador({
        "usuarios:1": ("string", '{"_id": "U1", "email": "a@x.com"}'),
        "usuarios:2": ("hash", {"_id": "U2", "email": "a@x.com"}),
        "usuarios:3": ("list", ["x"]),
        "usuarios:4": ("string", "no es json"),
        "usuarios:5": ("string", "42"),
    })
    assert [r["_id"] for r in adp.obtener_todos("usuarios")] == ["U1", "U2"]
    assert adp.contar_duplicados("usuarios", "email", "a@x.com") == 2
    assert adp.existe("usuarios", "_id", "U2")


def test_explorador_muestra_claves_sin_prefijo():
    adp = crear_adaptador({
        "contador": ("string", "7"),
        "usuarios:1": ("string", '{"_id": "U1"}'),
    })
    adp.listar_recursos = RedisAdapter.listar_recursos.__get__(adp)
    assert {r["nombre"] for r in adp.listar_recursos()} == {SIN_PREFIJO, "usuarios"}
    muestra = adp.obtener_muestra(SIN_PREFIJO)
    assert [m["_key"] for m in muestra] == ["contador"]
