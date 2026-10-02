import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo.supabase_client import SupabaseClient
from controlador.controlador_auth import ControladorAuth

st.set_page_config(page_title="Motor de Integridad Multibase de Datos No SQL", page_icon="🛡️", layout="wide")

if not SupabaseClient().get_client():
    st.error("🚨 **Error Crítico:** No se pudo conectar con Supabase. Revisa `.env`.")
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

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
    # Actualizar actividad
    usuario_actual = st.session_state.get('usuario')
    if usuario_actual:
        ControladorAuth().actualizar_actividad(usuario_actual)

    pg = st.navigation([dashboard, conexiones, monitor, reglas, verificacion, reportes, comunidad])
    
    st.sidebar.markdown(f"### 🛡️ Motor de Integridad Multibase de Datos No SQL")
    st.sidebar.markdown(f"**Workspace:** `{st.session_state.get('usuario')}`")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["logged_in"] = False
        st.session_state["usuario"] = None
        st.rerun()
else:
    pg = st.navigation([login_page])

pg.run()
