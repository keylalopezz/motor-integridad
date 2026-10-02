import os
import json
from typing import List, Dict, Any
import redis
from .base import Adaptador

class RedisAdapter(Adaptador):
    def __init__(self, config: Dict[str, Any] = None):
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
        import time
        started = time.perf_counter()
        self.client.ping()
        return {"estado": "Disponible", "latencia_ms": round((time.perf_counter() - started) * 1000, 2), "detalle": f"DB {self.client.connection_pool.connection_kwargs.get('db', 0)}"}

    def obtener_info_completa(self) -> Dict[str, Any]:
        import time
        started = time.perf_counter()
        self.client.ping()
        latencia = round((time.perf_counter() - started) * 1000, 2)

        info: Dict[str, Any] = {
            "motor": "Redis",
            "latencia_ms": latencia,
            "estado": "Disponible",
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
                prefijo = key.split(":", 1)[0] if ":" in key else "(sin prefijo)"
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
        conteos = {}
        for key in self.client.scan_iter(count=500):
            nombre = key.split(":", 1)[0]
            conteos[nombre] = conteos.get(nombre, 0) + 1
        return [{"nombre": nombre, "registros": cantidad} for nombre, cantidad in sorted(conteos.items())]

    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        muestra = []
        for key in self.client.scan_iter(match=f"{coleccion}:*", count=200):
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

    def _get_all_keys_in_collection(self, coleccion: str) -> List[str]:
        # Usar scan_iter para evitar bloquear el servidor con keys()
        return list(self.client.scan_iter(match=f"{coleccion}:*", count=1000))

    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        keys = self._get_all_keys_in_collection(coleccion)
        for key in keys:
            data = self.client.get(key)
            if data:
                try:
                    obj = json.loads(data)
                    if obj.get(campo) == valor:
                        return True
                except:
                    pass
        return False

    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        keys = self._get_all_keys_in_collection(coleccion)
        res = []
        for key in keys:
            data = self.client.get(key)
            if data:
                try:
                    obj = json.loads(data)
                    # Comprobar si cumple el filtro
                    match = True
                    for k, v in filtro.items():
                        if obj.get(k) != v:
                            match = False
                            break
                    if match:
                        res.append(obj)
                except:
                    pass
        return res

    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        keys = self._get_all_keys_in_collection(coleccion)
        count = 0
        for key in keys:
            data = self.client.get(key)
            if data:
                try:
                    obj = json.loads(data)
                    if obj.get(campo) == valor:
                        count += 1
                except:
                    pass
        return count

    def obtener_todos(self, coleccion: str) -> List[Dict]:
        return self.obtener(coleccion, {})

    def cerrar(self) -> None:
        self.client.close()
