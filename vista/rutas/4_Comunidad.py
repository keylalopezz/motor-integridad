import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_auth import ControladorAuth

st.title("🌍 Comunidad: Motor de Integridad Multibase de Datos No SQL")
st.markdown("Descubre quiénes están trabajando y protegiendo sus bases de datos en este momento.")

controlador = ControladorAuth()
# Consideramos activos a los que tuvieron actividad en los ultimos 5 minutos
usuarios_activos = controlador.obtener_usuarios_activos(minutos=5)

st.divider()

if not usuarios_activos:
    st.info("No hay otros usuarios conectados en este momento.")
else:
    st.subheader(f"🟢 Usuarios en línea ({len(usuarios_activos)})")
    
    # Mostrar usuarios en forma de tarjetas atractivas
    cols = st.columns(4)
    for idx, user in enumerate(usuarios_activos):
        with cols[idx % 4]:
            with st.container(border=True):
                # Si es el usuario actual, lo destacamos
                is_me = (user == st.session_state.get("usuario"))
                if is_me:
                    st.markdown(f"### 🧑‍💻 {user} (Tú)")
                    st.markdown("🟢 **Activo ahora**")
                else:
                    st.markdown(f"### 👤 {user}")
                    st.markdown("🟢 **Activo ahora**")
