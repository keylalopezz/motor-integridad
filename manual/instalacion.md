# Instalación y configuración

## Requisitos

- Python 3.12 (3.11 o superior)
- Un proyecto en [Supabase](https://supabase.com/)
- Opcional: bases de datos en MongoDB Atlas, Upstash (Redis) y DataStax Astra (Cassandra)

## 1. Clonar e instalar dependencias

```bash
git clone <url-del-repositorio>
cd motor-integridad
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## 2. Preparar Supabase

1. Crea un proyecto en Supabase.
2. En el *SQL Editor* ejecuta `supabase_schema.sql` (crea `usuarios_sistema`, `reglas`, `auditoria_violaciones`
   y `conexiones_motores`, y activa RLS).
3. Si el proyecto ya tiene datos, ejecuta en su lugar `supabase_migracion_seguridad.sql`.

## 3. Variables de entorno

Copia `.env.example` como `.env` y completa:

| Variable | Descripción |
|---|---|
| `SUPABASE_URL` | URL del proyecto de Supabase |
| `SUPABASE_KEY` | Clave *service_role* (la app corre en el servidor; RLS bloquea la clave pública) |
| `ENCRYPTION_KEY` | Clave Fernet que cifra las credenciales de los motores |

Genera la clave de cifrado con:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

!!! warning "No cambies la ENCRYPTION_KEY"
    Si se cambia después de guardar conexiones, estas ya no podrán descifrarse y habrá que registrarlas de nuevo.

`.env` y `.streamlit/secrets.toml` están en `.gitignore`: nunca se suben al repositorio.

## 4. Ejecutar la aplicación

```bash
streamlit run vista/app.py
```

## 5. Verificar las conexiones

```bash
python verificar_conexiones.py            # Supabase, ENCRYPTION_KEY y motores con credenciales en .env
python verificar_conexiones.py <usuario>  # motores que ese usuario guardó en la aplicación
```

## 6. Datos de prueba (opcional)

Los scripts `poblar_mongo.py`, `poblar_redis.py` y `poblar_cassandra.py` cargan un conjunto de datos con
violaciones inyectadas (usuarios, pedidos y pagos) para comprobar las cuatro reglas.
