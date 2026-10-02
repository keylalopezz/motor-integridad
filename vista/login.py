import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from controlador.controlador_auth import ControladorAuth

st.markdown("<h1 style='text-align: center; color: #f8fafc; font-size: 3rem;'>🛡️ Motor de Integridad Multibase de Datos No SQL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.2rem; margin-bottom: 2rem;'>Tu motor de integridad cloud-native</p>", unsafe_allow_html=True)

controlador = ControladorAuth()

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "✨ Crear Cuenta"])

    with tab1:
        st.markdown("### Accede a tu Workspace")
        user_login = st.text_input("Usuario", placeholder="ej. admin_saas")
        pass_login = st.text_input("Contraseña", type="password", placeholder="••••••••")
        submit_login = st.button("Ingresar al panel", use_container_width=True)
        
        if submit_login:
            if user_login and pass_login:
                exito, msj = controlador.login(user_login, pass_login)
                if exito:
                    st.session_state["logged_in"] = True
                    st.session_state["usuario"] = user_login
                    st.rerun()
                else:
                    st.error(f"❌ {msj}")
            else:
                st.warning("Completa ambos campos.")
                    
    with tab2:
        st.markdown("### Crea tu Tenant")
        user_reg = st.text_input("Nuevo Usuario (Tenant ID)")
        pass_reg = st.text_input("Nueva Contraseña", type="password")
        submit_reg = st.button("Registrarse", use_container_width=True)
        
        if submit_reg:
            if user_reg and pass_reg:
                exito, msj = controlador.registrar(user_reg, pass_reg)
                if exito:
                    st.success("✅ Cuenta creada con éxito. Ahora inicia sesión.")
                else:
                    st.error(f"❌ {msj}")
            else:
                st.warning("Completa ambos campos.")
