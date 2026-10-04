"""Adaptador de MongoDB Atlas basado en ``pymongo``."""

import os
from typing import List, Dict, Any
from pymongo import MongoClient
from .base import Adaptador

class MongoAdapter(Adaptador):
    """Acceso a una base de MongoDB: colecciones como recursos y documentos como registros."""
    def __init__(self, config: Dict[str, Any] = None):
        """Conecta con la URI y la base de datos indicadas en ``config``."""
        if config is None: config = {}
        uri = config.get("MONGO_URI", os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
        db_name = config.get("MONGO_DB", os.environ.get("MONGO_DB", "ecommerce_db"))
        self.client = MongoClient(uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
        self.db = self.client[db_name]

    def verificar_salud(self) -> Dict[str, Any]:
        """Ejecuta ``ping`` y devuelve el estado y la latencia en milisegundos."""
        started = __import__('time').perf_counter()
        self.client.admin.command("ping")
        return {"estado": "Disponible", "latencia_ms": round((__import__('time').perf_counter() - started) * 1000, 2), "detalle": self.db.name}

    def obtener_info_completa(self) -> Dict[str, Any]:
        """Devuelve versión, estadísticas del servidor, colecciones, índices y esquema inferido."""
        started = __import__('time').perf_counter()
        self.client.admin.command("ping")
        latencia = round((__import__('time').perf_counter() - started) * 1000, 2)

        info: Dict[str, Any] = {
            "motor": "MongoDB",
            "latencia_ms": latencia,
            "estado": "Disponible",
            "database": self.db.name,
            "servidor": {},
            "estadisticas": {},
            "colecciones": []
        }

        # 1. Informacion del servidor
        try:
            build_info = self.client.admin.command("buildInfo")
            info["servidor"] = {
                "version": build_info.get("version", "Desconocida"),
                "git_version": build_info.get("gitVersion", "N/D"),
                "max_wire_version": build_info.get("maxWireVersion", "N/D"),
                "bits": build_info.get("bits", 64)
            }
        except Exception:
            try:
                srv = self.client.server_info()
                info["servidor"] = {"version": srv.get("version", "Desconocida")}
            except Exception:
                info["servidor"] = {"version": "Disponible"}

        # 2. Estadísticas de la base de datos (dbStats)
        try:
            db_stats = self.db.command("dbStats")
            info["estadisticas"] = {
                "colecciones_total": db_stats.get("collections", len(self.db.list_collection_names())),
                "vistas_total": db_stats.get("views", 0),
                "objetos_total": db_stats.get("objects", 0),
                "tamano_datos_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                "tamano_almacenamiento_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
                "tamano_indices_mb": round(db_stats.get("indexSize", 0) / (1024 * 1024), 2),
                "indices_total": db_stats.get("indexes", 0),
                "tamano_promedio_objeto_kb": round(db_stats.get("avgObjSize", 0) / 1024, 2)
            }
        except Exception:
            info["estadisticas"] = {
                "colecciones_total": len(self.db.list_collection_names()),
                "tamano_datos_mb": "N/D",
                "tamano_almacenamiento_mb": "N/D",
                "tamano_indices_mb": "N/D",
                "indices_total": "N/D"
            }

        # 3. Detalle de cada coleccion con indices y esquema inferido
        for name in sorted(self.db.list_collection_names()):
            col = self.db[name]
            try:
                registros = col.estimated_document_count()
            except Exception:
                try:
                    registros = col.count_documents({})
                except Exception:
                    registros = None

            # Índices
            indices = []
            try:
                for idx_name, idx_val in col.index_information().items():
                    claves = ", ".join([f"{k}: {v}" for k, v in idx_val.get("key", [])])
                    indices.append({
                        "nombre": idx_name,
                        "campos": claves,
                        "unico": "Sí" if idx_val.get("unique") else "No"
                    })
            except Exception:
                pass

            # Inferencia de campos de muestra
            campos_detectados = {}
            try:
                muestra = list(col.find({}).limit(20))
                for doc in muestra:
                    for k, v in doc.items():
                        if k not in campos_detectados:
                            tipo_nombre = type(v).__name__
                            if tipo_nombre == "list":
                                tipo_nombre = "Array"
                            elif tipo_nombre == "dict":
                                tipo_nombre = "Objeto JSON"
                            elif tipo_nombre == "ObjectId":
                                tipo_nombre = "ObjectId (PK)"
                            elif tipo_nombre == "str":
                                tipo_nombre = "String"
                            elif tipo_nombre == "int":
                                tipo_nombre = "Integer"
                            elif tipo_nombre == "float":
                                tipo_nombre = "Double / Float"
                            elif tipo_nombre == "bool":
                                tipo_nombre = "Boolean"
                            campos_detectados[k] = tipo_nombre
            except Exception:
                pass

            info["colecciones"].append({
                "nombre": name,
                "registros": registros,
                "indices": indices,
                "campos": [{"campo": k, "tipo": v} for k, v in campos_detectados.items()]
            })

        return info

    def listar_recursos(self) -> List[Dict[str, Any]]:
        """Lista las colecciones con su cantidad estimada de documentos."""
        recursos = []
        for name in sorted(self.db.list_collection_names()):
            try:
                cantidad = self.db[name].estimated_document_count()
            except Exception:
                cantidad = None
            recursos.append({"nombre": name, "registros": cantidad})
        return recursos

    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        """Devuelve hasta ``limite`` documentos de ``coleccion``."""
        res = []
        for doc in self.db[coleccion].find({}).limit(limite):
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            res.append(doc)
        return res

    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        """Indica si algún documento de ``coleccion`` tiene ``campo`` igual a ``valor``."""
        col = self.db[coleccion]
        return col.count_documents({campo: valor}) > 0

    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        """Devuelve los documentos de ``coleccion`` que cumplen ``filtro``."""
        col = self.db[coleccion]
        # _id is typically an ObjectId which is not serializable easily.
        # For simplicity, if we need it, we convert to string
        res = []
        for doc in col.find(filtro):
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            res.append(doc)
        return res

    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        """Cuenta los documentos de ``coleccion`` con ``campo`` igual a ``valor``."""
        col = self.db[coleccion]
        return col.count_documents({campo: valor})

    def obtener_todos(self, coleccion: str) -> List[Dict]:
        """Devuelve todos los documentos de ``coleccion``."""
        return self.obtener(coleccion, {})

    def cerrar(self) -> None:
        """Cierra el cliente de MongoDB."""
        self.client.close()
