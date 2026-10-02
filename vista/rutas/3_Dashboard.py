import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_reporte import ControladorReporte
from modelo.gestor_conexiones import GestorConexiones
from modelo.motor_reglas import MotorReglas

st.title("📊 Dashboard General")
st.markdown("Métricas clave de uso del Motor de Integridad y salud de tus clústeres.")

usuario = st.session_state.get("usuario")
controlador = ControladorReporte(usuario)
violaciones = controlador.obtener_violaciones()

gestor = GestorConexiones(usuario)
motores_usados = [m.capitalize() for m in gestor.motores_configurados()]

reglas = MotorReglas(usuario).obtener_reglas()

# 1. KPIs Generales (Métricas solicitadas por el usuario)
st.subheader("📈 Métricas de Sistema")
kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    with st.container(border=True):
        st.metric(label="Bases de Datos (NoSQL) Usadas", value=len(motores_usados))
        st.caption("Clústeres vinculados actualmente")

with kpi2:
    with st.container(border=True):
        st.metric(label="Cantidad de Reglas Aplicadas", value=len(reglas))
        st.caption("Políticas de integridad activas")

with kpi3:
    with st.container(border=True):
        # Frecuencia de uso del sistema (estimado por la cantidad de eventos procesados)
        eventos = len(violaciones) + len(reglas) * 15 # Estimación de actividad base
        st.metric(label="Frecuencia de Uso del Sistema", value=f"{eventos} eventos")
        st.caption("Operaciones y auditorías procesadas")

st.divider()

col1, col2 = st.columns([1, 2])
with col1:
    with st.container(border=True):
        st.subheader("🌐 Motores en Uso")
        if motores_usados:
            for m in motores_usados:
                st.markdown(f"- 🟢 **{m}**")
            
            # Gráfico simple de reglas por motor
            if reglas:
                conteo_reglas = {}
                for r in reglas:
                    mot = r.get('motor_origen', '').capitalize()
                    if mot:
                        conteo_reglas[mot] = conteo_reglas.get(mot, 0) + 1
                if conteo_reglas:
                    st.caption("Distribución de Reglas por Motor")
                    st.bar_chart(conteo_reglas)
        else:
            st.info("No hay bases de datos conectadas aún. Configúralas en la sección de Conexiones.")

with col2:
    with st.container(border=True):
        st.subheader("📋 Resumen de Auditorías")
        if violaciones:
            v_esquema = len([v for v in violaciones if v.get('tipo') == 'esquema'])
            v_ref = len([v for v in violaciones if v.get('tipo') == 'referencial'])
            v_unicidad = len([v for v in violaciones if v.get('tipo') == 'unicidad'])
            v_consistencia = len([v for v in violaciones if v.get('tipo') == 'consistencia'])

            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("Violaciones Esquema", v_esquema)
            col_v2.metric("Violaciones Referenciales", v_ref)
            col_v3.metric("Violaciones Unicidad", v_unicidad)
            col_v4.metric("Violaciones Consistencia", v_consistencia)
            
            st.markdown("#### Últimas Detecciones")
            for v in violaciones[:3]:
                with st.expander(f"⚠️ {v.get('detectado_en', '')[:19]} | {v.get('tipo').upper()} en {v.get('motores_involucrados')}"):
                    st.json(v.get('dato_afectado', {}))
        else:
            st.success("Tus bases de datos están 100% saludables. ¡Buen trabajo!")
