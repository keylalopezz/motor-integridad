import streamlit as st
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.supabase_client import SupabaseClient
from controlador.controlador_auth import ControladorAuth
from modelo.supabase_client import obtener_config

st.set_page_config(page_title="Motor de Integridad Multibase de Datos No SQL", page_icon="🛡️", layout="wide")

if not SupabaseClient().get_client():
    st.error("🚨 **Error Crítico:** No se pudo conectar con Supabase. Revisa `.env`.")
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Sesión: expira tras SESION_MINUTOS sin actividad (30 por defecto)
SESION_MINUTOS = int(obtener_config("SESION_MINUTOS", "30") or 30)


def cerrar_sesion(motivo: str) -> None:
    """Cierra la sesión, registrando el evento (``logout`` o ``sesion_expirada``) con su duración."""
    usuario = st.session_state.get("usuario")
    inicio = st.session_state.get("inicio_sesion", time.time())
    if usuario:
        ControladorAuth().cerrar_sesion(usuario, motivo, round((time.time() - inicio) / 60, 1))
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]
    st.session_state["logged_in"] = False
    if motivo == "sesion_expirada":
        st.session_state["aviso_sesion"] = f"⏱️ Tu sesión expiró tras {SESION_MINUTOS} minutos sin actividad. Vuelve a iniciar sesión."

# CSS Premium (Glassmorphism, Google Fonts, Animaciones)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at top left, #0e101c, #05060b);
        color: #e2e8f0; 
    }
    
    [data-testid="stSidebar"] { 
        background-color: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }
    
    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea { 
        background-color: rgba(30, 41, 59, 0.7) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; 
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }
    
    /* Botones Premium */
    .stButton > button { 
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white; 
        border: none; 
        border-radius: 8px; 
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .stButton > button:hover { 
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
    }
    
    /* Expanders & Metrics */
    [data-testid="stExpander"] {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        backdrop-filter: blur(8px);
    }
    [data-testid="stMetricValue"] {
        color: #818cf8 !important;
    }
    
    hr { border-color: rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

login_page = st.Page("login.py", title="Acceso", icon="🔐")

conexiones = st.Page("rutas/0_Conexiones.py", title="Bases de Datos", icon="☁️")
monitor = st.Page("rutas/5_Monitor.py", title="Monitor", icon="🩺")
reglas = st.Page("rutas/1_Reglas.py", title="Reglas", icon="⚡")
verificacion = st.Page("rutas/2_Verificacion.py", title="Ejecución", icon="🚀")
dashboard = st.Page("rutas/3_Dashboard.py", title="Dashboard", icon="📊")
reportes = st.Page("rutas/6_Reportes.py", title="Reportes", icon="📄")
comunidad = st.Page("rutas/4_Comunidad.py", title="Comunidad", icon="🌍")

if st.session_state["logged_in"]:
    ahora = time.time()
    ultima = st.session_state.get("ultima_interaccion", ahora)
    if ahora - ultima > SESION_MINUTOS * 60:
        cerrar_sesion("sesion_expirada")
        st.rerun()
    st.session_state["ultima_interaccion"] = ahora
    st.session_state.setdefault("inicio_sesion", ahora)

    # Actividad para «Comunidad»: como máximo una escritura por minuto en Supabase
    usuario_actual = st.session_state.get('usuario')
    if usuario_actual and ahora - st.session_state.get("actividad_guardada", 0) > 60:
        ControladorAuth().actualizar_actividad(usuario_actual)
        st.session_state["actividad_guardada"] = ahora

    pg = st.navigation([dashboard, conexiones, monitor, reglas, verificacion, reportes, comunidad])
    
    st.sidebar.markdown(f"### 🛡️ Motor de Integridad Multibase de Datos No SQL")
    st.sidebar.markdown(f"**Workspace:** `{st.session_state.get('usuario')}`")
    minutos = int((ahora - st.session_state["inicio_sesion"]) // 60)
    st.sidebar.caption(f"🕑 Sesión activa hace {minutos} min · expira tras {SESION_MINUTOS} min sin actividad")
    st.sidebar.markdown("---")

    if st.sidebar.button("Cerrar Sesión"):
        cerrar_sesion("logout")
        st.rerun()
else:
    pg = st.navigation([login_page])

pg.run()
