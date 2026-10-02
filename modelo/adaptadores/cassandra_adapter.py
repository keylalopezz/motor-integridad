import os
from typing import List, Dict, Any
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from .base import Adaptador


def _q(identificador: str) -> str:
    """Cita un identificador CQL (tabla o columna) para admitir nombres como _id y evitar inyeccion."""
    return '"' + str(identificador).replace('"', '""') + '"'

class CassandraAdapter(Adaptador):
    def __init__(self, config: Dict[str, Any] = None):
        if config is None: config = {}
        self.keyspace = config.get("CASSANDRA_KEYSPACE", os.environ.get("CASSANDRA_KEYSPACE", "default_keyspace"))
        self._temp_bundle_path = None
        
        bundle_b64 = config.get("CASSANDRA_BUNDLE_B64")
        client_id = config.get("CASSANDRA_CLIENT_ID")
        client_secret = config.get("CASSANDRA_CLIENT_SECRET")
        
        if bundle_b64 and client_id and client_secret:
            import base64
            import tempfile
            
            # Crear un archivo temporal para el zip porque el driver exige una ruta física
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            temp_file.write(base64.b64decode(bundle_b64))
            temp_file.close()
            self._temp_bundle_path = temp_file.name
            
            cloud_config = {'secure_connect_bundle': self._temp_bundle_path}
            auth_provider = PlainTextAuthProvider(client_id, client_secret)
            self.cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider, connect_timeout=15)
        else:
            host = config.get("CASSANDRA_HOST", os.environ.get("CASSANDRA_HOST", "127.0.0.1"))
            port = int(config.get("CASSANDRA_PORT", os.environ.get("CASSANDRA_PORT", 9042)))
            auth_provider = None
            if config.get("CASSANDRA_USER"):
                auth_provider = PlainTextAuthProvider(config["CASSANDRA_USER"], config.get("CASSANDRA_PASSWORD", ""))
            self.cluster = Cluster([host], port=port, auth_provider=auth_provider, connect_timeout=10)
            
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

    def verificar_salud(self) -> Dict[str, Any]:
        import time
        started = time.perf_counter()
        self.session.execute("SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s", (self.keyspace,))
        return {"estado": "Disponible", "latencia_ms": round((time.perf_counter() - started) * 1000, 2), "detalle": self.keyspace}

    def obtener_info_completa(self) -> Dict[str, Any]:
        import time
        started = time.perf_counter()
        self.session.execute("SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s", (self.keyspace,))
        latencia = round((time.perf_counter() - started) * 1000, 2)

        info: Dict[str, Any] = {
            "motor": "Cassandra",
            "latencia_ms": latencia,
            "estado": "Disponible",
            "keyspace": self.keyspace,
            "cluster": {},
            "tablas": []
        }

        try:
            meta = self.cluster.metadata
            nodos = []
            for h in meta.all_hosts():
                nodos.append(f"{h.address} (DC: {h.datacenter}, Rack: {h.rack})")
            info["cluster"] = {
                "nombre": meta.cluster_name or "Cassandra Cluster",
                "particionador": meta.partitioner or "N/D",
                "nodos": nodos
            }
        except Exception:
            info["cluster"] = {"nombre": "N/D", "particionador": "N/D", "nodos": []}

        try:
            t_rows = self.session.execute(
                "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s", (self.keyspace,)
            )
            tablas_nombres = sorted([r["table_name"] for r in t_rows])

            for t_name in tablas_nombres:
                c_rows = self.session.execute(
                    "SELECT column_name, type, kind FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                    (self.keyspace, t_name)
                )
                columnas = []
                for c in c_rows:
                    rol = c["kind"]
                    if rol == "partition_key":
                        rol_str = "Partition Key 🔑"
                    elif rol == "clustering":
                        rol_str = "Clustering Key 📌"
                    else:
                        rol_str = "Columna regular"
                    columnas.append({
                        "columna": c["column_name"],
                        "tipo": c["type"],
                        "rol": rol_str
                    })

                info["tablas"].append({
                    "nombre": t_name,
                    "columnas": columnas,
                    "registros": None
                })
        except Exception:
            pass

        return info

    def listar_recursos(self) -> List[Dict[str, Any]]:
        rows = self.session.execute("SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s", (self.keyspace,))
        return [{"nombre": row["table_name"], "registros": None} for row in rows]

    def obtener_muestra(self, coleccion: str, limite: int = 20) -> List[Dict[str, Any]]:
        # El identificador procede de system_schema, no de entrada libre del usuario.
        permitidas = {item["nombre"] for item in self.listar_recursos()}
        if coleccion not in permitidas:
            raise ValueError("Tabla no encontrada en el keyspace configurado.")
        return list(self.session.execute(f'SELECT * FROM {_q(coleccion)} LIMIT %s', (limite,)))

    def existe(self, coleccion: str, campo: str, valor: Any) -> bool:
        # Cassandra requiere ALLOW FILTERING si no es partition key
        query = f"SELECT * FROM {_q(coleccion)} WHERE {_q(campo)} = %s LIMIT 1 ALLOW FILTERING"
        rows = self.session.execute(query, (valor,))
        return len(list(rows)) > 0

    def obtener(self, coleccion: str, filtro: Dict) -> List[Dict]:
        if not filtro:
            query = f"SELECT * FROM {_q(coleccion)}"
            return list(self.session.execute(query))
            
        campos = " AND ".join([f"{_q(k)} = %s" for k in filtro.keys()])
        valores = tuple(filtro.values())
        query = f"SELECT * FROM {_q(coleccion)} WHERE {campos} ALLOW FILTERING"
        return list(self.session.execute(query, valores))

    def contar_duplicados(self, coleccion: str, campo: str, valor: Any) -> int:
        query = f"SELECT COUNT(*) as count FROM {_q(coleccion)} WHERE {_q(campo)} = %s ALLOW FILTERING"
        rows = self.session.execute(query, (valor,))
        res = list(rows)
        return res[0]['count'] if res else 0

    def obtener_todos(self, coleccion: str) -> List[Dict]:
        return self.obtener(coleccion, {})

    def cerrar(self) -> None:
        self.session.shutdown()
        self.cluster.shutdown()
        
        if hasattr(self, '_temp_bundle_path') and self._temp_bundle_path:
            import os
            try:
                os.remove(self._temp_bundle_path)
            except:
                pass
