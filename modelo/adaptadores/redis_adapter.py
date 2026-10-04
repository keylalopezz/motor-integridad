"""Adaptador de Redis (Upstash). Una colección es el prefijo de las claves (``usuarios:``)."""

import os
import json
from typing import List, Dict, Any, Optional
import redis
from .base import Adaptador

# Nombre con el que se agrupan las claves sin ":" (no forman parte de ninguna coleccion)
SIN_PREFIJO = "(sin prefijo)"


def _prefijo(key: str) -> str:
    """Devuelve el prefijo de una clave (``usuarios:U001`` → ``usuarios``)."""
    return key.split(":", 1)[0] if ":" in key else SIN_PREFIJO


class RedisAdapter(Adaptador):
    """Acceso a Redis: lee registros guardados como JSON o como hash bajo un prefijo de clave."""
    def __init__(self, config: Dict[str, Any] = None):
        """Conecta con el host, puerto y contraseña de ``config`` (TLS para Upstash)."""
        if config is None: config = {}
        host = config.get("REDIS_HOST", os.environ.get("REDIS_HOST", "localhost"))
        port = int(config.get("REDIS_PORT", os.environ.get("REDIS_PORT", 6379)))
        db = int(config.get("REDIS_DB", os.environ.get("REDIS_DB", 0)))
        password = config.get("REDIS_PASSWORD", os.environ.get("REDIS_PASSWORD", None))
        
        # Limpieza robusta del host por si pegaron el puerto, espacios o protocolos
        host_limpio = host.strip()
        host_limpio = host_limpio.replace("redis://", "").replace("rediss://", "")
        host_limpio = host_limpio.replace("https://", "").replace("http://", "")
        if ":" in host_limpio:
            host_limpio = host_limpio.split(":")[0]
            
        usar_ssl = "upstash.io" in host_limpio.lower()
        self.host = host_limpio
        
        self.client = redis.Redis(
            host=host_limpio, 
            port=port, 
            db=db, 
            password=password, 
            decode_responses=True,
            ssl=usar_ssl,
            socket_timeout=8,
            socket_connect_timeout=8
        )

    def verificar_salud(self) -> Dict[str, Any]:
        """Ejecuta ``PING`` y devuelve el estado y la latencia en milisegundos."""
        import time
        started = time.perf_counter()
        self.client.ping()
        return {"estado": "Disponible", "latencia_ms": round((time.perf_counter() - started) * 1000, 2), "detalle": f"DB {self.client.connection_pool.connection_kwargs.get('db', 0)}"}

    def obtener_info_completa(self) -> Dict[str, Any]:
        """Devuelve versión, memoria, clientes, prefijos y una muestra de claves."""
        import time
        started = time.perf_counter()
        self.client.ping()
        latencia = round((time.perf_counter() - started) * 1000, 2)

        info: Dict[str, Any] = {
            "motor": "Redis",
            "latencia_ms": latencia,
            "estado": "Disponible",
            "host": self.host,
            "servidor": {},
            "memoria": {},
            "estadisticas": {},
            "recursos": []
        }

        try:
            raw_info = self.client.info()
            info["servidor"] = {
                "version": raw_info.get("redis_version", "Desconocida"),
                "modo": raw_info.get("redis_mode", "standalone"),
                "so": raw_info.get("os", "N/D"),
                "uptime_dias": raw_info.get("uptime_in_days", 0),
                "puerto": raw_info.get("tcp_port", 6379),
            }
            info["memoria"] = {
                "usada_humana": raw_info.get("used_memory_human", "N/D"),
                "pico_humana": raw_info.get("used_memory_peak_human", "N/D"),
                "fragmentacion": raw_info.get("mem_fragmentation_ratio", "N/D"),
                "politica_eviccion": raw_info.get("maxmemory_policy", "noeviction")
            }
            info["estadisticas"] = {
                "clientes_conectados": raw_info.get("connected_clients", 0),
                "comandos_procesados": raw_info.get("total_commands_processed", 0),
                "conexiones_totales": raw_info.get("total_connections_received", 0),
                "claves_expiradas": raw_info.get("expired_keys", 0),
                "claves_desalojadas": raw_info.get("evicted_keys", 0)
            }
        except Exception:
            pass

        # Desglose de claves por prefijo/namespace con scan_iter (sin bloquear)
        prefijos = {}
        total_escaneado = 0
        try:
            for key in self.client.scan_iter(count=500):
                total_escaneado += 1
                prefijo = _prefijo(key)
                if prefijo not in prefijos:
                    prefijos[prefijo] = {"nombre": prefijo, "registros": 0, "tipos": set(), "muestra_claves": []}
                prefijos[prefijo]["registros"] += 1
                if len(prefijos[prefijo]["muestra_claves"]) < 5:
                    prefijos[prefijo]["muestra_claves"].append(key)
                if len(prefijos[prefijo]["tipos"]) < 3 and total_escaneado <= 200:
                    try:
                        ktype = self.client.type(key)
                        prefijos[prefijo]["tipos"].add(ktype)
                    except Exception:
                        pass
                if total_escaneado >= 5000:
                    break

            for p in prefijos.values():
                info["recursos"].append({
                    "nombre": p["nombre"],
                    "registros": p["registros"],
                    "tipos": list(p["tipos"]) if p["tipos"] else ["string"],
                    "claves_ejemplo": p["muestra_claves"]
                })
        except Exception:
            pass

        return info

    def listar_recursos(self) -> List[Dict[str, Any]]:
        """Lista los prefijos de clave con la cantidad de claves de cada uno."""
        conteos = {}
        for key in self.client.scan_iter(count=500):
            nombre = _prefijo(key)
            conteos[nombre] = conteos.get(nombre, 0) + 1
        return [{"nombre": nombre, "registros": cantidad} for nombre, cantidad in sorted(conteos.items())]

    def _claves(self, coleccion: str, count: int = 1000):
        # Usar scan_iter para evitar bloquear el servidor con keys()
        """Itera las claves que pertenecen al prefijo ``coleccion``."""
        if coleccion == SIN_PREFIJO:
            return (k for k in self.client.scan_iter(count=count) if ":" not in k)
        return self.client.scan_iter(match=f"{coleccion}:*", count=count)

    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        """Devuelve hasta ``limite`` registros del prefijo ``coleccion``."""
        muestra = []
        for key in self._claves(coleccion, count=200):
            tipo = self.client.type(key)
            if tipo == "string":
                data = self.client.get(key)
                try:
                    valor = json.loads(data) if data else None
                except (TypeError, json.JSONDecodeError):
                    valor = data
            elif tipo == "hash":
                valor = self.client.hgetall(key)
            elif tipo == "list":
                valor = self.client.lrange(key, 0, max(limite - 1, 0))
            elif tipo == "set":
                valor = sorted(self.client.smembers(key))[:limite]
            elif tipo == "zset":
                valor = self.client.zrange(key, 0, max(limite - 1, 0), withscores=True)
            elif tipo == "stream":
                valor = self.client.xrevrange(key, count=limite)
            else:
                valor = f"Tipo de clave no soportado: {tipo}"
            muestra.append({"_key": key, "tipo": tipo, "valor": valor})
            if len(muestra) >= limite:
                break
        return muestra

    def _leer_registro(self, key: str) -> Optional[Dict]:
        """Un registro es un string con un objeto JSON o un hash. Las demas estructuras se ignoran."""
        try:
            obj = json.loads(self.client.get(key) or "null")
        except redis.exceptions.ResponseError:
            # WRONGTYPE: la clave no es un string
            try:
                return self.client.hgetall(key) if self.client.type(key) == "hash" else None
            except redis.exceptions.ResponseError:
                return None
        except ValueError:
            # El string no es JSON
            return None
        return obj if isinstance(obj, dict) else None

    def _registros(self, coleccion: str):
        """Itera los registros (diccionarios) del prefijo ``coleccion``."""
        for key in self._claves(coleccion):
            obj = self._leer_registro(key)
            if obj is not None:
                yield obj

    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        """Indica si algún registro del prefijo tiene ``campo`` igual a ``valor``."""
        return any(obj.get(campo) == valor for obj in self._registros(coleccion))

    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        """Devuelve los registros del prefijo que cumplen todos los pares de ``filtro``."""
        return [obj for obj in self._registros(coleccion)
                if all(obj.get(k) == v for k, v in filtro.items())]

    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        """Cuenta los registros del prefijo con ``campo`` igual a ``valor``."""
        return sum(1 for obj in self._registros(coleccion) if obj.get(campo) == valor)

    def obtener_todos(self, coleccion: str) -> List[Dict]:
        """Devuelve todos los registros del prefijo ``coleccion``."""
        return self.obtener(coleccion, {})

    def cerrar(self) -> None:
        """Cierra la conexión con Redis."""
        self.client.close()
