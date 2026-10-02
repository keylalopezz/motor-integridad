import json
import redis

print("🌟 Bienvenido al Poblador de Datos de Prueba para REDIS 🌟")
print("Ve a tu panel de Upstash (o tu proveedor de Redis) y copia las credenciales:")
host = input("👉 REDIS_HOST (ej. un-nombre.upstash.io): ").strip()
port = input("👉 REDIS_PORT (ej. 34523): ").strip()
password = input("👉 REDIS_PASSWORD: ").strip()

if not host or not port:
    print("❌ Error: Host y puerto son obligatorios.")
    exit(1)

try:
    print("\nConectando a Redis...")
    host_limpio = host.strip()
    host_limpio = host_limpio.replace("redis://", "").replace("rediss://", "")
    host_limpio = host_limpio.replace("https://", "").replace("http://", "")
    if ":" in host_limpio:
        host_limpio = host_limpio.split(":")[0]
        
    usar_ssl = "upstash.io" in host_limpio.lower()
    client = redis.Redis(
        host=host_limpio, 
        port=int(port), 
        password=password if password else None, 
        decode_responses=True,
        ssl=usar_ssl,
        socket_timeout=5
    )
    
    # Comprobar conexión
    client.ping()
    print("✅ Conectado exitosamente. Insertando datos...")

    # --- 1. DATOS DE USUARIOS ---
    # En Redis las colecciones se simulan usando prefijos en las claves (coleccion:id)
    usuarios_data = [
        {"_id": "U001", "nombre": "Ana Pérez", "email": "ana@email.com", "edad": 28, "estado": "activo"},
        {"_id": "U002", "nombre": "Carlos Gómez", "email": "carlos@email.com", "edad": 35, "estado": "activo"},
        # ❌ Usuario sin email (Esquema)
        {"_id": "U003", "nombre": "Usuario Sin Email", "edad": 40, "estado": "inactivo"},
        # ❌ Email duplicado (Unicidad)
        {"_id": "U004", "nombre": "Clon de Ana", "email": "ana@email.com", "edad": 22, "estado": "activo"}
    ]
    
    # Limpiar datos viejos
    for key in client.scan_iter("usuarios:*"): client.delete(key)
    
    for u in usuarios_data:
        client.set(f"usuarios:{u['_id']}", json.dumps(u))
    print(f"👉 Insertados {len(usuarios_data)} registros con prefijo 'usuarios:'")

    # --- 2. DATOS DE PEDIDOS ---
    pedidos_data = [
        {"_id": "P100", "usuario_id": "U001", "producto": "Laptop", "total": 1200.50},
        {"_id": "P101", "usuario_id": "U002", "producto": "Mouse Inalámbrico", "total": 25.00},
        # ❌ Pedido Huérfano (Referencial)
        {"_id": "P102", "usuario_id": "U999", "producto": "Teclado Mecánico", "total": 85.00}
    ]
    
    # Limpiar datos viejos
    for key in client.scan_iter("pedidos:*"): client.delete(key)
    
    for p in pedidos_data:
        client.set(f"pedidos:{p['_id']}", json.dumps(p))
    print(f"👉 Insertados {len(pedidos_data)} registros con prefijo 'pedidos:'")

    print("\n🎉 ¡Datos cargados en Redis con éxito!")
    print("En tu app, estas claves se verán como la colección 'usuarios' y 'pedidos'.")

except Exception as e:
    print(f"\n❌ Ocurrió un error: {e}")
