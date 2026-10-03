"""Verifica la conexion con Supabase y con los motores NoSQL configurados en .env.

Uso: python verificar_conexiones.py            -> Supabase y motores con credenciales en .env
     python verificar_conexiones.py <usuario>  -> motores guardados por ese usuario en la app
Los motores sin credenciales en .env se omiten.
"""
import base64
import os
from dotenv import load_dotenv

load_dotenv()

TABLAS = ["usuarios_sistema", "reglas", "auditoria_violaciones", "conexiones_motores"]


def verificar_supabase():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        return None, "faltan SUPABASE_URL / SUPABASE_KEY"
    from supabase import create_client
    cliente = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    for tabla in TABLAS:
        cliente.table(tabla).select("*", count="exact").limit(1).execute()
    return True, "tablas: " + ", ".join(TABLAS)


def verificar_encryption_key():
    clave = os.environ.get("ENCRYPTION_KEY")
    if not clave:
        return None, "falta ENCRYPTION_KEY"
    from cryptography.fernet import Fernet
    f = Fernet(clave.encode("utf-8"))
    assert f.decrypt(f.encrypt(b"ok")) == b"ok"
    return True, "clave Fernet valida"


def _probar(adaptador):
    try:
        salud = adaptador.verificar_salud()
        recursos = [r["nombre"] for r in adaptador.listar_recursos()]
        return True, f"{salud['latencia_ms']} ms, recursos: {recursos or 'ninguno'}"
    finally:
        adaptador.cerrar()


def verificar_mongo():
    if not (os.environ.get("MONGO_URI") and os.environ.get("MONGO_DB")):
        return None, "faltan MONGO_URI / MONGO_DB"
    from modelo.adaptadores import MongoAdapter
    return _probar(MongoAdapter({"MONGO_URI": os.environ["MONGO_URI"], "MONGO_DB": os.environ["MONGO_DB"]}))


def verificar_redis():
    if not os.environ.get("REDIS_HOST"):
        return None, "falta REDIS_HOST"
    from modelo.adaptadores import RedisAdapter
    return _probar(RedisAdapter({
        "REDIS_HOST": os.environ["REDIS_HOST"],
        "REDIS_PORT": int(os.environ.get("REDIS_PORT") or 6379),
        "REDIS_PASSWORD": os.environ.get("REDIS_PASSWORD") or None,
    }))


def verificar_cassandra():
    ruta = os.environ.get("CASSANDRA_BUNDLE_PATH")
    datos = [os.environ.get(k) for k in ("CASSANDRA_KEYSPACE", "CASSANDRA_CLIENT_ID", "CASSANDRA_CLIENT_SECRET")]
    if not (ruta and all(datos)):
        return None, "faltan CASSANDRA_KEYSPACE / CASSANDRA_BUNDLE_PATH / CASSANDRA_CLIENT_ID / CASSANDRA_CLIENT_SECRET"
    from modelo.adaptadores import CassandraAdapter
    with open(ruta, "rb") as f:
        bundle_b64 = base64.b64encode(f.read()).decode("utf-8")
    return _probar(CassandraAdapter({
        "CASSANDRA_KEYSPACE": datos[0],
        "CASSANDRA_BUNDLE_B64": bundle_b64,
        "CASSANDRA_CLIENT_ID": datos[1],
        "CASSANDRA_CLIENT_SECRET": datos[2],
    }))


def verificar_motores_de_usuario(usuario: str):
    """Prueba los motores con las credenciales que el usuario guardo en la app (cifradas en Supabase)."""
    from modelo.adaptadores import get_adapter
    from modelo.gestor_conexiones import GestorConexiones

    gestor = GestorConexiones(usuario)
    existe = gestor.supabase.table("usuarios_sistema").select("usuario").eq("usuario", usuario).execute().data
    if not existe:
        print(f"[ERROR  ] El usuario '{usuario}' no existe en la app (usuarios_sistema).")
        return
    configurados = gestor.motores_configurados()
    print(f"Motores guardados por '{usuario}': {configurados or 'ninguno'}")
    for motor in configurados:
        try:
            ok, detalle = _probar(get_adapter(motor, usuario))
        except Exception as e:
            ok, detalle = False, f"{type(e).__name__}: {e}"
        print(f"[{'OK     ' if ok else 'ERROR  '}] {motor} (guardado en la app): {detalle}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        verificar_motores_de_usuario(sys.argv[1])
        sys.exit()
    pruebas = [
        ("Supabase", verificar_supabase),
        ("ENCRYPTION_KEY", verificar_encryption_key),
        ("MongoDB", verificar_mongo),
        ("Redis", verificar_redis),
        ("Cassandra", verificar_cassandra),
    ]
    for nombre, prueba in pruebas:
        try:
            ok, detalle = prueba()
        except Exception as e:
            ok, detalle = False, f"{type(e).__name__}: {e}"
        estado = {True: "OK     ", False: "ERROR  ", None: "OMITIDO"}[ok]
        print(f"[{estado}] {nombre}: {detalle}")
