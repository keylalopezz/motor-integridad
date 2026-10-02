import os
from getpass import getpass
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

print("🌟 Bienvenido al Poblador de Datos de Prueba para CASSANDRA (DataStax Astra) 🌟")
print("Necesitas el Secure Connect Bundle (.zip) y el token generado en Astra.")
bundle = input("👉 Ruta del Secure Connect Bundle (.zip): ").strip().strip('"')
keyspace = input("👉 Keyspace (ej. tienda): ").strip()
client_id = input("👉 Client ID (o la palabra token): ").strip()
# getpass no muestra el secreto en pantalla
client_secret = getpass("👉 Client Secret (o el token AstraCS:...). Pégalo con CLIC DERECHO, no se mostrará: ").strip()
# Ctrl+V en un campo oculto de PowerShell inserta un caracter de control en vez de pegar
client_secret = "".join(c for c in client_secret if c.isprintable())

print(f"\nClient ID recibido: '{client_id}'")
print(f"Secret recibido: {len(client_secret)} caracteres, empieza por '{client_secret[:8]}...'")
if client_id.lower() == "token" and not client_secret.startswith("AstraCS:"):
    print("⚠️ Con Client ID 'token', el secret debe ser el token que empieza por 'AstraCS:'.")

if not (bundle and keyspace and client_id and client_secret):
    print("❌ Error: todos los datos son obligatorios.")
    exit(1)
if not os.path.isfile(bundle):
    print(f"❌ Error: no se encontró el archivo {bundle}")
    exit(1)

try:
    print("\nConectando a Cassandra (puede tardar unos segundos)...")
    cluster = Cluster(cloud={"secure_connect_bundle": bundle},
                      auth_provider=PlainTextAuthProvider(client_id, client_secret),
                      connect_timeout=20)
    session = cluster.connect(keyspace)
    print("✅ Conectado exitosamente. Creando tabla e insertando datos...")

    # --- TABLA: PAGOS ---
    # En la tienda, Cassandra guarda el historial de pagos (escrituras masivas).
    session.execute("DROP TABLE IF EXISTS pagos")
    session.execute("""
        CREATE TABLE pagos (
            id text PRIMARY KEY,
            pedido_id text,
            transaccion text,
            monto double,
            metodo text
        )
    """)

    pagos_data = [
        # ✅ Pagos correctos (pedidos que existen en MongoDB)
        ("PA1", "P100", "TX-1001", 1200.50, "tarjeta"),
        ("PA2", "P101", "TX-1002", 25.00, "yape"),
        # ❌ Pago de un pedido que NO existe (para reglas REFERENCIALES cassandra -> mongodb)
        ("PA3", "P999", "TX-1003", 85.00, "tarjeta"),
        # ❌ Doble cobro: repite la transacción de PA1 (para reglas de UNICIDAD)
        ("PA4", "P100", "TX-1001", 1200.50, "tarjeta"),
    ]
    insert = session.prepare("INSERT INTO pagos (id, pedido_id, transaccion, monto, metodo) VALUES (?, ?, ?, ?, ?)")
    for p in pagos_data:
        session.execute(insert, p)
    print(f"👉 Insertados {len(pagos_data)} registros en 'pagos'.")

    print("\n🎉 ¡Datos de prueba cargados en Cassandra con éxito!")
    print("Ya puedes conectar Cassandra en la app y crear reglas sobre la tabla 'pagos'.")
    cluster.shutdown()

except Exception as e:
    print(f"\n❌ Ocurrió un error al conectar o insertar: {e}")
