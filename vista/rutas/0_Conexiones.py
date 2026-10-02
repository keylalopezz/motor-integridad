import streamlit as st
import base64
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modelo.gestor_conexiones import GestorConexiones
from modelo.adaptadores import MongoAdapter, RedisAdapter, CassandraAdapter

usuario = st.session_state.get("usuario")
gestor = GestorConexiones(usuario)

st.title("☁️ Conexiones Cloud")
st.markdown("Vincula tus clústeres NoSQL. Las conexiones están aisladas de forma segura en tu workspace.")

try:
    configurados = gestor.motores_configurados()
except Exception:
    configurados = []
if configurados:
    st.caption("Conectados: " + " · ".join(f"🟢 {m}" for m in configurados))


def probar_y_guardar(motor: str, clase_adaptador, config: dict, probar_solo: bool):
    adapter = None
    try:
        with st.spinner(f"Probando conexión con {motor.upper()}..."):
            adapter = clase_adaptador(config)
            salud = adapter.verificar_salud()
        st.success(f"✅ Conexión correcta ({salud.get('latencia_ms')} ms).")
    except Exception as e:
        st.error(f"❌ No se pudo conectar: {type(e).__name__}: {e}")
        return
    finally:
        if adapter:
            try:
                adapter.cerrar()
            except Exception:
                pass
    if not probar_solo:
        gestor.guardar_conexion(motor, config)
        st.switch_page("rutas/5_Monitor.py")


def botones(motor: str, clase_adaptador, config: dict):
    b1, b2 = st.columns(2)
    if b1.button("🔌 Probar conexión", use_container_width=True, key=f"probar_{motor}"):
        probar_y_guardar(motor, clase_adaptador, config, probar_solo=True)
    if b2.button(f"💾 Probar y guardar", type="primary", use_container_width=True, key=f"guardar_{motor}"):
        probar_y_guardar(motor, clase_adaptador, config, probar_solo=False)
    if motor in configurados and st.button("🗑️ Eliminar conexión guardada", use_container_width=True, key=f"borrar_{motor}"):
        gestor.eliminar_conexion(motor)
        st.rerun()


# Usamos st.selectbox para que sea un combo box desplegable como pidió el usuario
opciones_motores = ["-- Seleccionar motor --", "MongoDB (Atlas)", "Redis (Upstash)", "Cassandra (Astra DB)"]
seleccionado = st.selectbox("Base de datos a conectar", opciones_motores)

st.divider()

if seleccionado == "-- Seleccionar motor --":
    st.info("💡 Haz clic en el menú desplegable de arriba y selecciona la base de datos NoSQL que deseas configurar.")
else:
    # Centramos el formulario usando columnas para que se vea mas estético
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if seleccionado == "MongoDB (Atlas)":
            with st.container(border=True):
                st.markdown("### 🍃 Configurar MongoDB")

                with st.expander("📖 ¿Cómo obtengo mi URI de MongoDB? (Guía rápida)"):
                    st.markdown("""
                    1. Entra a [MongoDB Atlas](https://www.mongodb.com/atlas/database) y crea un clúster gratis.
                    2. En 'Database Access', crea un usuario y contraseña.
                    3. En 'Network Access', añade la IP `0.0.0.0/0` para permitir la conexión.
                    4. Haz clic en **Connect > Drivers**, y copia la URL.
                    5. Pégala abajo y **reemplaza `<password>`** por tu contraseña real.
                    """)

                config_mongo = gestor.obtener_conexion("mongodb") or {}
                mongo_uri = st.text_input("URI de Conexión", value=config_mongo.get("MONGO_URI", ""), placeholder="mongodb+srv://...", type="password")
                mongo_db = st.text_input("Database Name", value=config_mongo.get("MONGO_DB", ""), placeholder="my_database")

                if mongo_uri and mongo_db:
                    botones("mongodb", MongoAdapter, {"MONGO_URI": mongo_uri.strip(), "MONGO_DB": mongo_db.strip()})
                else:
                    st.caption("Completa la URI y el nombre de la base de datos.")

        elif seleccionado == "Redis (Upstash)":
            with st.container(border=True):
                st.markdown("### ⚡ Configurar Redis")

                with st.expander("📖 ¿Cómo obtengo mis datos de Redis? (Guía rápida)"):
                    st.markdown("""
                    1. Entra a [Upstash](https://upstash.com/) y dale a **Create Database** (Redis).
                    2. Ponle un nombre y dale a crear.
                    3. Cuando cargue, baja por la pantalla y verás tu **Endpoint** (es el Host) y tu **Password**.
                    4. El **Puerto** siempre son los números al final del endpoint (ej. `32512`).
                    """)

                config_redis = gestor.obtener_conexion("redis") or {}
                redis_host = st.text_input("Host", value=config_redis.get("REDIS_HOST", ""), placeholder="us1-redis.upstash.io")
                redis_port = st.text_input("Puerto", value=str(config_redis.get("REDIS_PORT", "6379")))
                redis_db = st.text_input("DB Index", value=str(config_redis.get("REDIS_DB", "0")))
                redis_password = st.text_input("Password", value=config_redis.get("REDIS_PASSWORD") or "", type="password")

                if redis_host:
                    botones("redis", RedisAdapter, {
                        "REDIS_HOST": redis_host.strip(),
                        "REDIS_PORT": int(redis_port) if redis_port.isdigit() else 6379,
                        "REDIS_DB": int(redis_db) if redis_db.isdigit() else 0,
                        "REDIS_PASSWORD": redis_password.strip() if redis_password.strip() else None
                    })
                else:
                    st.caption("Completa al menos el Host.")

        elif seleccionado == "Cassandra (Astra DB)":
            with st.container(border=True):
                st.markdown("### 👁️ Configurar Cassandra")

                with st.expander("📖 ¿Cómo conecto DataStax Astra DB? (Guía rápida)"):
                    st.markdown("""
                    1. Entra a [Astra DB](https://astra.datastax.com/) y crea una base de datos **Serverless (Vector)** o clásica.
                    2. Crea un **keyspace** (ej. `ecommerce`).
                    3. En **Connect**, descarga el **Secure Connect Bundle** (.zip).
                    4. Genera un **Application Token**: el *Client ID* y *Client Secret* van abajo
                       (si solo tienes el token `AstraCS:...`, usa `token` como Client ID y el token como Secret).
                    """)

                config_cass = gestor.obtener_conexion("cassandra") or {}
                modo = st.radio("Tipo de clúster", ["Astra DB (Secure Bundle)", "Host propio"], horizontal=True)
                keyspace = st.text_input("Keyspace", value=config_cass.get("CASSANDRA_KEYSPACE", ""))

                if modo == "Astra DB (Secure Bundle)":
                    bundle = st.file_uploader("Secure Connect Bundle (.zip)", type=["zip"])
                    if config_cass.get("CASSANDRA_BUNDLE_B64") and not bundle:
                        st.caption("✅ Ya hay un bundle guardado; sube otro solo si quieres reemplazarlo.")
                    client_id = st.text_input("Client ID", value=config_cass.get("CASSANDRA_CLIENT_ID", ""))
                    client_secret = st.text_input("Client Secret", value=config_cass.get("CASSANDRA_CLIENT_SECRET", ""), type="password")
                    bundle_b64 = base64.b64encode(bundle.getvalue()).decode("utf-8") if bundle else config_cass.get("CASSANDRA_BUNDLE_B64")
                    config = {
                        "CASSANDRA_KEYSPACE": keyspace.strip(),
                        "CASSANDRA_BUNDLE_B64": bundle_b64,
                        "CASSANDRA_CLIENT_ID": client_id.strip(),
                        "CASSANDRA_CLIENT_SECRET": client_secret.strip(),
                    }
                    completo = keyspace and bundle_b64 and client_id and client_secret
                else:
                    host = st.text_input("Host", value=config_cass.get("CASSANDRA_HOST", ""))
                    port = st.text_input("Puerto", value=str(config_cass.get("CASSANDRA_PORT", "9042")))
                    user = st.text_input("Usuario (opcional)", value=config_cass.get("CASSANDRA_USER", ""))
                    password = st.text_input("Password (opcional)", value=config_cass.get("CASSANDRA_PASSWORD", ""), type="password")
                    config = {
                        "CASSANDRA_KEYSPACE": keyspace.strip(),
                        "CASSANDRA_HOST": host,
                        "CASSANDRA_PORT": int(port) if port.isdigit() else 9042,
                        "CASSANDRA_USER": user,
                        "CASSANDRA_PASSWORD": password,
                    }
                    completo = keyspace and host

                if completo:
                    botones("cassandra", CassandraAdapter, config)
                else:
                    st.caption("Completa el keyspace y las credenciales.")
