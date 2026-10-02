import os
from pymongo import MongoClient

print("🌟 Bienvenido al Poblador de Datos de Prueba para MongoDB 🌟")
uri = input("👉 Pega aquí tu URI de MongoDB (mongodb+srv://...): ").strip()
db_name = input("👉 Ingresa el nombre de tu base de datos (ej. mi_tienda): ").strip()

if not uri or not db_name:
    print("❌ Error: Necesitas ingresar la URI y el nombre de la base de datos.")
    exit(1)

try:
    print("\nConectando a MongoDB...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    
    # Limpiamos las colecciones por si se ejecuta varias veces
    db.usuarios.drop()
    db.pedidos.drop()
    
    print("✅ Conectado exitosamente. Insertando datos...")

    # --- 1. COLECCIÓN: USUARIOS ---
    usuarios_data = [
        # ✅ Usuarios correctos
        {"_id": "U001", "nombre": "Ana Pérez", "email": "ana@email.com", "edad": 28, "estado": "activo"},
        {"_id": "U002", "nombre": "Carlos Gómez", "email": "carlos@email.com", "edad": 35, "estado": "activo"},
        
        # ❌ Usuario sin email (Para que pruebes reglas de ESQUEMA)
        {"_id": "U003", "nombre": "Usuario Sin Email", "edad": 40, "estado": "inactivo"},
        
        # ❌ Usuario con email duplicado de Ana (Para que pruebes reglas de UNICIDAD)
        {"_id": "U004", "nombre": "Clon de Ana", "email": "ana@email.com", "edad": 22, "estado": "activo"}
    ]
    db.usuarios.insert_many(usuarios_data)
    print(f"👉 Insertados {len(usuarios_data)} registros en 'usuarios'.")

    # --- 2. COLECCIÓN: PEDIDOS ---
    pedidos_data = [
        # ✅ Pedidos correctos (hacen referencia a usuarios que sí existen)
        {"_id": "P100", "usuario_id": "U001", "producto": "Laptop", "total": 1200.50},
        {"_id": "P101", "usuario_id": "U002", "producto": "Mouse Inalámbrico", "total": 25.00},
        
        # ❌ Pedido Huérfano (Hace referencia a un usuario 'U999' que NO existe. Para que pruebes reglas REFERENCIALES)
        {"_id": "P102", "usuario_id": "U999", "producto": "Teclado Mecánico", "total": 85.00}
    ]
    db.pedidos.insert_many(pedidos_data)
    print(f"👉 Insertados {len(pedidos_data)} registros en 'pedidos'.")

    print("\n🎉 ¡Datos de prueba cargados con éxito!")
    print("Ya puedes ir a la aplicación, crear reglas sobre estas colecciones y usar el 'Scan Batch' para que el motor detecte los errores intencionales.")

except Exception as e:
    print(f"\n❌ Ocurrió un error al conectar o insertar: {e}")
