import streamlit as st
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_verificacion import ControladorVerificacion

st.title("🚀 Centro de Ejecución")

usuario = st.session_state.get("usuario")
controlador = ControladorVerificacion(usuario)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    with st.container(border=True):
        st.subheader("🛠️ Simulador Pre-escritura")
        st.markdown("Prueba un documento antes de insertarlo (Verifica Schema y Unicidad).")
        motor = st.selectbox("Motor", ["mongodb", "redis", "cassandra"])
        coleccion = st.text_input("Colección")
        registro_str = st.text_area("Payload (JSON)", value='{\n  "id": 1,\n  "nombre": "Test"\n}', height=150)
        
        if st.button("Ejecutar Validación", width="stretch"):
            if not coleccion:
                st.warning("Indica la colección a validar.")
                st.stop()
            try:
                registro = json.loads(registro_str)
                valido, mensaje = controlador.validar_insercion(motor, coleccion, registro)
                if valido:
                    st.success(f"✅ {mensaje}")
                else:
                    st.error(f"❌ {mensaje}")
            except json.JSONDecodeError as e:
                st.error(f"Payload JSON inválido: {e}")
            except Exception as e:
                st.error(f"Error de motor: {e}")

with col2:
    with st.container(border=True):
        st.subheader("🕵️ Scan Batch")
        st.markdown("Ejecuta un escaneo profundo inter-bases para detectar huérfanos y desincronizaciones.")
        
        st.info("Dependiendo del volumen de datos en la nube, esto puede tomar unos segundos.")
        
        if st.button("Iniciar Escaneo Profundo", type="primary", width="stretch"):
            with st.spinner("Conectando con motores y escaneando datos..."):
                try:
                    violaciones, errores = controlador.ejecutar_verificacion_batch()
                    for err in errores:
                        st.error(f"⚠️ {err}")
                    if violaciones:
                        st.warning(f"⚠️ Se detectaron {len(violaciones)} anomalías en tus bases de datos.")
                    elif not errores:
                        st.success("✨ Escaneo finalizado. Bases de datos íntegras.")
                except Exception as e:
                    st.error(f"Error en ejecución: {e}")
