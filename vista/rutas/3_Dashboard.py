import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_reporte import ControladorReporte
from modelo.gestor_conexiones import GestorConexiones
from modelo.motor_reglas import MotorReglas
from modelo.metricas_uso import MetricasUso, ACCIONES
import pandas as pd

st.title("📊 Dashboard General")
st.markdown("Métricas clave de uso del Motor de Integridad y salud de tus clústeres.")

usuario = st.session_state.get("usuario")
try:
    violaciones = ControladorReporte(usuario).obtener_violaciones()
    motores_usados = [m.capitalize() for m in GestorConexiones(usuario).motores_configurados()]
    reglas = MotorReglas(usuario).obtener_reglas()
except Exception as e:
    st.error(f"❌ No se pudieron cargar los datos desde Supabase: {type(e).__name__}. Intenta recargar en unos segundos.")
    st.stop()

# 1. KPIs Generales
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
        st.metric(label="Anomalías Detectadas", value=len(violaciones))
        ultimo = max((v.get('detectado_en') or '' for v in violaciones), default='')
        st.caption(f"Último escaneo con hallazgos: {ultimo[:16].replace('T', ' ')} UTC" if ultimo else "Sin anomalías registradas")

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

st.divider()
st.subheader("📈 Utilización del Producto")
col_f1, col_f2 = st.columns([1, 1])
dias = col_f1.selectbox("Periodo", [7, 30, 90], index=1, format_func=lambda d: f"Últimos {d} días")
alcance = col_f2.radio("Alcance", ["Mi cuenta", "Toda la plataforma"], horizontal=True)
eventos = MetricasUso(usuario).obtener_eventos(dias=dias, todos=alcance == "Toda la plataforma")

if eventos is None:
    st.info("Las métricas de uso se activan al aplicar la migración `eventos_uso` (Liquibase, ver README).")
elif not eventos:
    st.info("Aún no hay actividad registrada en este periodo.")
else:
    df = pd.DataFrame(eventos)
    df["fecha"] = pd.to_datetime(df["creado_en"], utc=True, format="ISO8601").dt.date
    df["accion"] = df["accion"].map(lambda a: ACCIONES.get(a, a))

    u1, u2, u3, u4 = st.columns(4)
    u1.metric("Eventos registrados", len(df))
    u2.metric("Usuarios activos", df["usuario"].nunique())
    u3.metric("Escaneos Batch", int((df["accion"] == ACCIONES["escaneo"]).sum()))
    u4.metric("Validaciones", int((df["accion"] == ACCIONES["validacion"]).sum()))

    g1, g2 = st.columns([2, 1])
    with g1:
        with st.container(border=True):
            st.caption("Actividad diaria por tipo de acción")
            por_dia = df.pivot_table(index="fecha", columns="accion", values="usuario", aggfunc="count", fill_value=0)
            st.bar_chart(por_dia)
    with g2:
        with st.container(border=True):
            st.caption("Uso por funcionalidad")
            st.bar_chart(df["accion"].value_counts(), horizontal=True)
    if alcance == "Toda la plataforma":
        with st.container(border=True):
            st.caption("Usuarios con más actividad")
            st.dataframe(df["usuario"].value_counts().rename("eventos").head(10))
